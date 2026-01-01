"""
SWARM ANALYSIS segment generator

Deep-dive token analysis using all SWARM agents (PERCEPTRON + FOOLIO + AZOKA).
"""

import logging
from ..models import SegmentContext, SegmentOutput
from .base import SegmentGenerator

logger = logging.getLogger(__name__)


class SwarmAnalysisGenerator(SegmentGenerator):
    """Generate content for SWARM ANALYSIS segment"""

    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        """
        Generate SWARM ANALYSIS segment content

        Workflow:
        1. Select token to analyze (from featured_tokens or trending)
        2. Run full SWARM analysis (PERCEPTRON + FOOLIO + AZOKA)
        3. Format comprehensive analysis notes
        """
        try:
            # Get token to analyze
            token_address = None
            ticker = None

            if context.featured_tokens:
                token_address = context.featured_tokens[0]
                ticker = "TOKEN"  # Would need to look up actual ticker
            else:
                # Default to a popular token
                ticker = "PEPE"
                logger.info("No featured token, using default: PEPE")

            if not self.swarm:
                return SegmentOutput(
                    speaker_notes="SWARM API not available",
                    featured_tokens=[],
                    swarm_analyses=[]
                )

            # Run full SWARM analysis
            analysis = await self.swarm.analyze_token(
                ticker=ticker,
                token_address=token_address
            )

            # Format speaker notes
            speaker_notes = self._format_swarm_analysis(ticker, analysis)

            return SegmentOutput(
                speaker_notes=speaker_notes,
                featured_tokens=[{"ticker": ticker, "address": token_address}],
                swarm_analyses=[analysis],
                metadata={"analyzed_token": ticker}
            )

        except Exception as e:
            logger.error(f"Error generating SWARM_ANALYSIS segment: {e}", exc_info=True)
            return SegmentOutput(
                speaker_notes=f"SWARM analysis error: {str(e)}",
                featured_tokens=[],
                swarm_analyses=[]
            )

    def _format_swarm_analysis(self, ticker: str, analysis: dict) -> str:
        """Format comprehensive SWARM analysis"""
        lines = [
            "=== SWARM ANALYSIS ===",
            "",
            f"Token: ${ticker}",
            "",
            "PERCEPTRON (Charts & Risk):",
            f"  • Regime: {analysis.get('regime', 'Unknown')}",
            f"  • Confidence: {analysis.get('confidence', 0)*100:.1f}%",
            f"  • Risk Score: {analysis.get('risk_score', 0):.2f}",
            f"  • Position: {analysis.get('position_recommendation', 'None')}",
            "",
            "FOOLIO (Social & Narrative):",
            f"  • Narrative Phase: {analysis.get('narrative_phase', 'Unknown')}",
            f"  • Social Sentiment: {self._get_sentiment_emoji(analysis)}",
            "",
            "AZOKA (Divergence & Judgment):",
            f"  • Response: {analysis.get('azoka_response', 'Pass')}",
            f"  • Divergence: {'🚨 DETECTED' if analysis.get('divergence_detected') else '✅ None'}",
            f"  • Chromatic State: {analysis.get('chromatic_state', 'Unknown')}",
            "",
            "FINAL ASSESSMENT:",
            f"  {self._generate_final_assessment(analysis)}"
        ]

        return "\n".join(lines)

    def _get_sentiment_emoji(self, analysis: dict) -> str:
        """Get emoji for sentiment"""
        phase = analysis.get('narrative_phase', '').lower()
        if 'peak' in phase or 'euphoria' in phase:
            return "🚀 Euphoric"
        elif 'discovery' in phase or 'validation' in phase:
            return "📈 Building"
        elif 'doubt' in phase or 'decline' in phase:
            return "📉 Declining"
        else:
            return "➡️ Neutral"

    def _generate_final_assessment(self, analysis: dict) -> str:
        """Generate final trading assessment"""
        regime = analysis.get('regime', '').lower()
        risk = analysis.get('risk_score', 0.5)
        divergence = analysis.get('divergence_detected', False)

        if divergence:
            return "⚠️  CAUTION: Divergence detected. Price and narrative misaligned."

        if 'breakout' in regime and risk < 0.5:
            return "🟢 OPPORTUNITY: Low risk breakout forming."

        if 'euphoria' in regime or risk > 0.7:
            return "🔴 HIGH RISK: Euphoric conditions, consider taking profits."

        if 'accumulation' in regime:
            return "🟡 WATCH: Accumulation phase, build position carefully."

        return "⚪ NEUTRAL: No strong signal, monitor for changes."
