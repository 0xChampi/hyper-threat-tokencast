"""
TOKEN LAUNCH LIVE segment generator

Monitors pump.fun for recent token launches and analyzes top ones with SWARM.
"""

import logging
from ..models import SegmentContext, SegmentOutput
from .base import SegmentGenerator

logger = logging.getLogger(__name__)


class TokenLaunchGenerator(SegmentGenerator):
    """Generate content for TOKEN LAUNCH LIVE segment"""

    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        """
        Generate TOKEN LAUNCH LIVE segment content

        Workflow:
        1. Get launches from past 5 minutes (pump.fun)
        2. Analyze top 3 with SWARM (regime + narrative)
        3. Format speaker notes with launch details + analysis
        """
        try:
            # Get recent launches if pump.fun client available
            launches = []
            if self.pump_fun:
                launches = await self.pump_fun.detect_launches(lookback_minutes=5)
                launches = launches[:3]  # Top 3

            if not launches:
                # Fallback if no launches or no client
                return SegmentOutput(
                    speaker_notes=self._generate_fallback_notes(),
                    featured_tokens=[],
                    swarm_analyses=[]
                )

            # Analyze each launch with SWARM
            analyses = []
            featured_tokens = []

            for launch in launches:
                token_data = {
                    "token_address": launch.get("token_address"),
                    "ticker": launch.get("ticker", "UNKNOWN"),
                    "discovered_at": launch.get("discovered_at"),
                    "price": launch.get("price_at_discovery")
                }
                featured_tokens.append(token_data)

                # Get SWARM analysis if available
                if self.swarm:
                    try:
                        analysis = await self.swarm.analyze_token(
                            ticker=token_data["ticker"],
                            token_address=token_data["token_address"]
                        )
                        analyses.append({
                            "token": token_data["ticker"],
                            "regime": analysis.get("regime", "Unknown"),
                            "narrative_phase": analysis.get("narrative_phase", "Unknown"),
                            "risk_score": analysis.get("risk_score", 0.5)
                        })
                    except Exception as e:
                        logger.error(f"SWARM analysis failed for {token_data['ticker']}: {e}")

            # Format speaker notes
            speaker_notes = self._format_token_launch_notes(launches, analyses)

            return SegmentOutput(
                speaker_notes=speaker_notes,
                featured_tokens=featured_tokens,
                swarm_analyses=analyses,
                metadata={"launch_count": len(launches)}
            )

        except Exception as e:
            logger.error(f"Error generating TOKEN_LAUNCH segment: {e}", exc_info=True)
            return SegmentOutput(
                speaker_notes=f"Error generating content: {str(e)}",
                featured_tokens=[],
                swarm_analyses=[]
            )

    def _generate_fallback_notes(self) -> str:
        """Fallback notes when no launches available"""
        return """
TOKEN LAUNCH LIVE

No new launches detected in the past 5 minutes.
The pump.fun pipeline is quiet right now.

We'll check back next segment for fresh deployments.
        """.strip()

    def _format_token_launch_notes(self, launches: list, analyses: list) -> str:
        """Format speaker notes for token launches"""
        lines = [
            "=== TOKEN LAUNCH LIVE ===",
            "",
            f"Detected {len(launches)} fresh launches in the past 5 minutes:",
            ""
        ]

        for i, launch in enumerate(launches):
            ticker = launch.get("ticker", "UNKNOWN")
            price = launch.get("price_at_discovery", 0)
            address = launch.get("token_address", "")[:10]

            lines.append(f"{i+1}. ${ticker}")
            lines.append(f"   Address: {address}...")
            lines.append(f"   Launch Price: ${price:.8f}")

            # Add SWARM analysis if available
            if i < len(analyses):
                analysis = analyses[i]
                lines.append(f"   Regime: {analysis.get('regime')}")
                lines.append(f"   Narrative: {analysis.get('narrative_phase')}")
                risk = analysis.get('risk_score', 0.5)
                lines.append(f"   Risk: {risk:.2f} ({'HIGH' if risk > 0.7 else 'MEDIUM' if risk > 0.4 else 'LOW'})")

            lines.append("")

        return "\n".join(lines)
