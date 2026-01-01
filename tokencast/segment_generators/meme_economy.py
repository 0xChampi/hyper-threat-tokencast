"""
MEME ECONOMY segment generator

Tracks trending meme coins via FOOLIO narrative intelligence.
"""

import logging
from ..models import SegmentContext, SegmentOutput
from .base import SegmentGenerator

logger = logging.getLogger(__name__)


class MemeEconomyGenerator(SegmentGenerator):
    """Generate content for MEME ECONOMY segment"""

    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        """
        Generate MEME ECONOMY segment content

        Workflow:
        1. Get trending meme coins (pump.fun or predefined list)
        2. Analyze narrative phases with FOOLIO
        3. Highlight which memes are meta
        """
        # Popular meme coins to analyze
        meme_coins = [
            {"ticker": "PEPE", "name": "Pepe"},
            {"ticker": "DOGE", "name": "Dogecoin"},
            {"ticker": "SHIB", "name": "Shiba Inu"},
            {"ticker": "WIF", "name": "Dogwifhat"},
            {"ticker": "BONK", "name": "Bonk"}
        ]

        speaker_notes = ["=== MEME ECONOMY ===", "", "Tracking narrative phases across top meme coins:", ""]

        analyses = []

        for coin in meme_coins[:3]:  # Top 3
            if self.swarm:
                try:
                    # Query SWARM about narrative
                    result = await self.swarm.query(
                        f"What's the narrative phase on ${coin['ticker']}?",
                        ticker=coin['ticker']
                    )

                    narrative = result.get('narrative_phase', 'Unknown')
                    analyses.append({
                        "token": coin['ticker'],
                        "narrative_phase": narrative
                    })

                    speaker_notes.append(f"${coin['ticker']} ({coin['name']})")
                    speaker_notes.append(f"  Narrative: {narrative}")
                    speaker_notes.append(f"  {self._get_phase_commentary(narrative)}")
                    speaker_notes.append("")

                except Exception as e:
                    logger.error(f"Error analyzing {coin['ticker']}: {e}")

        speaker_notes.append("The meme economy is constantly evolving - stay vigilant!")

        return SegmentOutput(
            speaker_notes="\n".join(speaker_notes),
            featured_tokens=meme_coins[:3],
            swarm_analyses=analyses,
            metadata={"meme_count": len(meme_coins)}
        )

    def _get_phase_commentary(self, narrative: str) -> str:
        """Get commentary based on narrative phase"""
        if not narrative or narrative == "Unknown":
            return "  📊 No strong narrative signal"

        phase = narrative.lower()
        if 'discovery' in phase:
            return "  🔍 Early stage - watch for validation"
        elif 'validation' in phase:
            return "  📈 Building momentum"
        elif 'peak' in phase:
            return "  🚀 Peak hype - consider exit timing"
        elif 'doubt' in phase:
            return "  ⚠️  Losing steam"
        elif 'dead' in phase:
            return "  💀 Narrative collapsed"
        else:
            return "  ➡️  Monitoring"
