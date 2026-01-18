"""CLI entry point for PolyHedge."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from polyhedge.config import get_settings
from polyhedge.logger import get_logger
from polyhedge.services.bundle_generator import BundleGenerator
from polyhedge.services.market_search import MarketSearch

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="polyhedge")
def cli():
    """PolyHedge: IRL Insurance via Polymarket.

    Hedge your real-life risks with prediction market bets.
    """
    pass


@cli.command()
@click.option(
    "--budget",
    "-b",
    type=float,
    default=100.0,
    help="Budget for hedging in USD (default: $100)",
)
@click.option(
    "--concern",
    "-c",
    type=str,
    default=None,
    help="Describe your primary concern (or enter interactively)",
)
@click.option(
    "--markets",
    "-m",
    type=int,
    default=500,
    help="Number of markets to search (default: 500)",
)
def hedge(budget: float, concern: str | None, markets: int):
    """Analyze your concern and recommend hedge bets."""
    logger.info("=" * 60)
    logger.info("PolyHedge session started")
    logger.info(f"Budget: ${budget}")

    try:
        settings = get_settings()
        logger.debug("Settings loaded successfully")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("Make sure ANTHROPIC_API_KEY and CEREBRAS_API_KEY are set")
        raise SystemExit(1)

    # Get concern from user if not provided
    if concern is None:
        console.print(
            Panel(
                "Describe your primary concern or risk you want to hedge.\n"
                "Be specific about what you're worried about.",
                title="PolyHedge",
                border_style="blue",
            )
        )
        concern = click.prompt("\nYour concern")

    logger.info(f"User concern: {concern[:200]}...")
    console.print()

    # Initialize services
    logger.debug("Initializing services")
    from polyhedge.services.concern_search import ConcernSearch
    from polyhedge.services.cerebras_filter import CerebrasMarketFilter
    from polyhedge.services.context_gatherer import ContextGatherer

    concern_search = ConcernSearch(settings)
    cerebras_filter = CerebrasMarketFilter(settings)
    bundle_generator = BundleGenerator(settings)
    context_gatherer = ContextGatherer(settings)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Gather web context
            logger.info("Step 1: Gathering web context")
            task = progress.add_task(
                "Gathering and compressing web context...",
                total=None
            )

            web_context = context_gatherer.gather_concern_context(
                concern=concern,
                num_results=5,
                max_tokens=1000
            )

            if web_context:
                logger.info(f"Web context gathered: {len(web_context)} chars")
            else:
                logger.warning("No web context available (compression may be disabled)")

            progress.update(task, completed=True)

            # Step 2: Search markets
            logger.info("Step 2: Searching markets via vector embeddings")
            progress.update(task, description=f"Searching {markets} markets related to your concern...")

            search_results = concern_search.search(
                concern=concern,
                n_results=markets,
                min_liquidity=100.0
            )

            if not search_results:
                logger.warning("No markets found")
                console.print("[yellow]No markets found.[/yellow]")
                console.print("Run [bold]polyhedge update-markets[/bold] and [bold]polyhedge update-vectors[/bold] first.")
                raise SystemExit(1)

            # Extract just the Market objects (drop similarity scores)
            market_list = [m for m, score in search_results]

            progress.update(task, completed=True)
            logger.info(f"Found {len(market_list)} markets")

            # Step 3: Filter with Cerebras (5 batches of 100 → 50 total)
            logger.info("Step 3: Filtering markets with Cerebras")
            progress.update(
                task,
                description=f"Filtering {len(market_list)} markets (5 batches)..."
            )

            filtered_markets = cerebras_filter.filter_in_batches(
                markets=market_list,
                user_concern=concern,
                batch_size=100,
                top_k_per_batch=10,
                web_context=web_context
            )

            progress.update(task, completed=True)
            logger.info(f"Filtered to {len(filtered_markets)} markets")

            if not filtered_markets:
                logger.warning("No relevant markets after filtering")
                console.print("[yellow]No relevant markets found for your concern.[/yellow]")
                raise SystemExit(1)

            # Step 4: Generate ETF bundles
            logger.info("Step 4: Generating ETF bundles")
            progress.update(task, description="Creating themed hedge portfolios...")

            bundles = bundle_generator.generate_etf_bundles(
                markets=filtered_markets,
                user_concern=concern,
                budget=budget,
                web_context=web_context
            )

            progress.update(task, completed=True)
            logger.info(f"Generated {len(bundles)} themed bundles")

        # Display results
        _display_etf_bundles(bundles, concern)
        logger.info("Session completed successfully")
        logger.info("=" * 60)

    except ValueError as e:
        if "Market cache is empty" in str(e) or "Vector DB not available" in str(e):
            logger.error("Market cache or vector DB not ready")
            console.print(f"[red]Error:[/red] {e}")
            console.print("\nPlease run these commands first:")
            console.print("[bold]  1. polyhedge update-markets[/bold]")
            console.print("[bold]  2. polyhedge update-vectors[/bold]")
            raise SystemExit(1)
        else:
            logger.error(f"Error during execution: {e}", exc_info=True)
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    finally:
        concern_search.close()
        cerebras_filter.close()
        context_gatherer.close()


def _display_etf_bundles(bundles, concern: str):
    """Display the ETF-style hedge bundles."""
    console.print()
    console.print(
        Panel(
            f"[bold]Concern:[/bold] {concern}\n"
            f"[bold]Total Bundles:[/bold] {len(bundles)}",
            title="Hedge Strategy",
            border_style="green",
        )
    )

    for i, bundle in enumerate(bundles, 1):
        console.print()
        console.print(f"\n[bold cyan]═══ Bundle {i}: {bundle.coverage_summary.split(':')[0]} ═══[/bold cyan]")
        console.print(f"[dim]{bundle.coverage_summary}[/dim]")
        console.print(f"[bold]Allocated:[/bold] ${bundle.total_allocated:.2f}")

        if bundle.bets:
            table = Table(show_header=True, title=f"Markets in Bundle {i}")
            table.add_column("#", style="dim")
            table.add_column("Market", style="bold", max_width=50)
            table.add_column("Bet", justify="center")
            table.add_column("Price", justify="right")
            table.add_column("Allocation", justify="right")
            table.add_column("Payout", justify="right")

            for j, bet in enumerate(bundle.bets, 1):
                table.add_row(
                    str(j),
                    bet.market.market.question[:50] + "..." if len(bet.market.market.question) > 50 else bet.market.market.question,
                    f"[green]{bet.outcome}[/green]" if bet.outcome.lower() == "yes" else f"[red]{bet.outcome}[/red]",
                    f"${bet.current_price:.2f}",
                    f"${bet.allocation:.2f}",
                    f"${bet.potential_payout:.2f}"
                )

            console.print(table)

    console.print()
    console.print(
        "[dim]Note: These are recommendations only. No orders are placed. "
        "Always do your own research before placing bets.[/dim]"
    )


def _display_risk_analysis(risk_analysis):
    """Display the risk analysis results."""
    console.print()
    console.print(
        Panel(
            f"[bold]{risk_analysis.situation_summary}[/bold]\n\n"
            f"Overall Risk Level: [{'red' if risk_analysis.overall_risk_level == 'high' else 'yellow' if risk_analysis.overall_risk_level == 'medium' else 'green'}]{risk_analysis.overall_risk_level.upper()}[/]",
            title="Risk Analysis",
            border_style="cyan",
        )
    )

    if risk_analysis.risk_factors:
        table = Table(title="Identified Risk Factors", show_header=True)
        table.add_column("Risk", style="bold")
        table.add_column("Category")
        table.add_column("Description")

        for factor in risk_analysis.risk_factors:
            table.add_row(factor.name, factor.category, factor.description[:80] + "..." if len(factor.description) > 80 else factor.description)

        console.print(table)


def _display_bundle(bundle):
    """Display the hedge bundle recommendations."""
    console.print()

    if not bundle.bets:
        console.print(
            Panel(
                "[yellow]No suitable hedges found for your situation.[/yellow]\n\n"
                "This could mean:\n"
                "- No prediction markets match your specific risks\n"
                "- Available markets have insufficient liquidity\n"
                "- Your risks are too specific or niche",
                title="Hedge Recommendations",
                border_style="yellow",
            )
        )
        return

    console.print(
        Panel(
            f"[bold]Budget:[/bold] ${bundle.budget:,.2f}\n"
            f"[bold]Total Allocated:[/bold] ${bundle.total_allocated:,.2f}\n"
            f"[bold]Coverage:[/bold] {bundle.coverage_summary}",
            title="Hedge Bundle",
            border_style="green",
        )
    )

    table = Table(title="Recommended Bets", show_header=True)
    table.add_column("#", style="dim")
    table.add_column("Market", style="bold", max_width=50)
    table.add_column("Bet", justify="center")
    table.add_column("Price", justify="right")
    table.add_column("Allocation", justify="right")
    table.add_column("Payout", justify="right")
    table.add_column("Multiplier", justify="right")

    for i, bet in enumerate(bundle.bets, 1):
        table.add_row(
            str(i),
            bet.market.market.question[:50] + "..." if len(bet.market.market.question) > 50 else bet.market.market.question,
            f"[green]{bet.outcome}[/green]" if bet.outcome.lower() == "yes" else f"[red]{bet.outcome}[/red]",
            f"${bet.current_price:.2f}",
            f"${bet.allocation:.2f}",
            f"${bet.potential_payout:.2f}",
            f"{bet.payout_multiplier:.1f}x",
        )

    console.print(table)

    # Show explanations
    console.print()
    console.print("[bold]Why these markets?[/bold]")
    for i, bet in enumerate(bundle.bets, 1):
        console.print(f"  {i}. {bet.market.correlation_explanation}")

    console.print()
    console.print(
        "[dim]Note: This is a recommendation only. No orders are placed. "
        "Always do your own research before placing bets.[/dim]"
    )


@cli.command()
def update_markets():
    """Fetch all markets from Polymarket and update the local market database.

    This fetches market data and saves it to the SQLite cache (polyhedge.db).
    Run this first, then run update-vectors to generate embeddings.
    """
    logger.info("Update markets command started")

    try:
        settings = get_settings()
    except Exception:
        # Don't need API key for this
        from polyhedge.config import Settings
        settings = Settings.__new__(Settings)
        settings.gamma_api_base_url = "https://gamma-api.polymarket.com"

    console.print(
        Panel(
            "Fetching all markets from Polymarket and updating local database.\n"
            "This may take a few minutes...",
            title="Update Market Database",
            border_style="blue",
        )
    )

    market_search = MarketSearch(settings, use_vector_search=False)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching markets from Polymarket API...", total=None)
            count = market_search.update_cache()
            progress.update(task, completed=True)

        console.print(f"\n[green]✓[/green] Successfully cached {count:,} markets in database")
        console.print(f"[dim]Database location: polyhedge.db\n")
        console.print("Next step: Run [bold]polyhedge update-vectors[/bold] to generate embeddings for semantic search.")
        logger.info(f"Markets updated successfully: {count} markets")

    except Exception as e:
        logger.error(f"Error updating markets: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    finally:
        market_search.close()


@cli.command()
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=100,
    help="Number of markets to process per batch (default: 100)",
)
@click.option(
    "--resume",
    "-r",
    is_flag=True,
    help="Resume from where it left off (skip already embedded markets)",
)
def update_vectors(batch_size: int, resume: bool):
    """Generate vector embeddings for semantic search.

    This reads markets from the local database and generates vector embeddings.
    The embedding generation can take time, so it's done in batches.
    Use --resume to continue if interrupted.
    """
    logger.info("Update vectors command started")

    from polyhedge.services.cache import MarketCache

    console.print(
        Panel(
            f"Generating vector embeddings for semantic search.\n"
            f"Batch size: {batch_size} markets\n"
            f"Resume mode: {'enabled' if resume else 'disabled'}\n\n"
            "This may take several minutes depending on the number of markets...",
            title="Update Vector Database",
            border_style="blue",
        )
    )

    cache = MarketCache(use_vectors=True)

    if not cache.vector_db:
        console.print("[red]Error:[/red] Vector database not available.")
        console.print("Make sure chromadb and sentence-transformers are installed.")
        raise SystemExit(1)

    try:
        # Get total count for progress
        markets = cache.get_markets()
        if not markets:
            console.print("[yellow]No markets found in database.[/yellow]")
            console.print("Run [bold]polyhedge update-markets[/bold] first to fetch markets.")
            raise SystemExit(1)

        total_markets = len(markets)

        if resume:
            existing_count = len(cache.vector_db.get_existing_ids())
            console.print(f"[dim]Found {existing_count:,} existing embeddings\n")

        # Calculate total batches
        total_batches = (total_markets + batch_size - 1) // batch_size

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Generating embeddings...",
                total=total_batches
            )

            def update_progress(current: int, total: int):
                progress.update(task, completed=current, total=total)

            cache.update_vector_db(
                batch_size=batch_size,
                resume=resume,
                progress_callback=update_progress
            )

        final_count = cache.vector_db.count()
        console.print(f"\n[green]✓[/green] Vector database updated successfully")
        console.print(f"[dim]Total vectors: {final_count:,}")
        console.print(f"[dim]Vector DB location: vector_db/\n")
        console.print("You can now run [bold]polyhedge hedge[/bold] to analyze your risks with semantic search.")
        logger.info(f"Vectors updated successfully: {final_count} embeddings")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted![/yellow]")
        console.print("Progress has been saved. Run with [bold]--resume[/bold] to continue:")
        console.print(f"  [bold]polyhedge update-vectors --resume --batch-size {batch_size}[/bold]")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Error updating vectors: {e}", exc_info=True)
        console.print(f"\n[red]Error:[/red] {e}")
        console.print("\nIf interrupted, you can resume with:")
        console.print(f"  [bold]polyhedge update-vectors --resume --batch-size {batch_size}[/bold]")
        raise SystemExit(1)


@cli.command()
def markets():
    """List currently active markets from Polymarket."""
    try:
        settings = get_settings()
    except Exception:
        # Don't need API key for this
        from polyhedge.config import Settings
        settings = Settings.__new__(Settings)
        settings.gamma_api_base_url = "https://gamma-api.polymarket.com"

    market_search = MarketSearch(settings)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching markets from Polymarket...", total=None)
            markets = market_search._fetch_markets(limit=20)
            progress.update(task, completed=True)

        if not markets:
            console.print("[yellow]No active markets found.[/yellow]")
            return

        table = Table(title="Active Polymarket Markets", show_header=True)
        table.add_column("Question", style="bold", max_width=60)
        table.add_column("Prices", justify="right")
        table.add_column("Liquidity", justify="right")

        for market in markets[:20]:
            prices = ", ".join(f"{o.name}: ${o.price:.2f}" for o in market.outcomes) if market.outcomes else "N/A"
            table.add_row(
                market.question[:60] + "..." if len(market.question) > 60 else market.question,
                prices,
                f"${market.liquidity:,.0f}",
            )

        console.print(table)

    finally:
        market_search.close()


if __name__ == "__main__":
    cli()
