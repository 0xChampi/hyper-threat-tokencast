"""
GAMBA Segment Generator - Rock Paper Scissors

Interactive rock-paper-scissors gambling segment where GIZMO plays against the community.

Flow:
1. GIZMO announces rock-paper-scissors round
2. Community places bets + picks (ROCK/PAPER/SCISSORS)
3. GIZMO makes its choice
4. Resolve winners (beat GIZMO = 2x, tie = 1x, lose = 0x)
5. Leaderboard updates
"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal
import random

from ..models import SegmentContext, SegmentOutput
from .base import SegmentGenerator


class GambaSegmentGenerator(SegmentGenerator):
    """
    GAMBA Segment - Rock Paper Scissors vs GIZMO

    Community plays rock-paper-scissors against GIZMO for crypto/points.
    """

    async def generate_content(self, context: SegmentContext) -> SegmentOutput:
        """
        Generate GAMBA rock-paper-scissors segment

        Steps:
        1. Create RPS round
        2. Set betting window
        3. Generate GIZMO's taunt/flavor text
        4. Format speaker notes
        5. Return segment with game metadata
        """

        # Create RPS round
        rps_round = await self._create_rps_round(context)

        # Get GIZMO's trash talk
        gizmo_taunt = self._get_gizmo_taunt()

        # Format speaker notes
        speaker_notes = self._format_gamba_notes(
            rps_round,
            gizmo_taunt,
            context
        )

        return SegmentOutput(
            speaker_notes=speaker_notes,
            featured_tokens=[],
            swarm_analyses=[],
            extra_metadata={
                "game_type": "rock_paper_scissors",
                "round_id": rps_round["round_id"],
                "betting_closes_at": rps_round["closes_at"],
                "gizmo_choice": rps_round["gizmo_choice_hash"],  # Hidden until reveal
                "payouts": rps_round["payouts"],
                "status": "betting_open"
            }
        )

    async def _create_rps_round(self, context: SegmentContext) -> Dict:
        """
        Create rock-paper-scissors round

        GIZMO makes choice in advance (hashed for fairness),
        reveals at end of betting window
        """
        now = datetime.utcnow()
        segment_duration = context.segment_config.duration_seconds if context.segment_config else 300
        betting_window = min(segment_duration - 60, 240)  # Leave 60s for resolution
        closes_at = now + timedelta(seconds=betting_window)

        # GIZMO makes choice (could use SWARM for "strategic" choice based on meta)
        gizmo_choice = await self._get_gizmo_choice(context)

        # Hash the choice for provable fairness
        choice_hash = self._hash_choice(gizmo_choice, context.show_id, context.segment_number)

        return {
            "round_id": f"rps_{context.show_id}_{context.segment_number}",
            "show_id": context.show_id,
            "segment_number": context.segment_number,
            "gizmo_choice": gizmo_choice,  # Hidden from API until reveal
            "gizmo_choice_hash": choice_hash,  # Public for verification
            "choices": ["ROCK", "PAPER", "SCISSORS"],
            "started_at": now.isoformat(),
            "closes_at": closes_at.isoformat(),
            "betting_window_seconds": betting_window,
            "status": "betting_open",
            "payouts": {
                "WIN": 2.0,   # Beat GIZMO = 2x your bet
                "TIE": 1.0,   # Tie = get bet back
                "LOSS": 0.0   # Lose = lose your bet
            },
            "total_pool": 0.0,
            "bet_counts": {
                "ROCK": 0,
                "PAPER": 0,
                "SCISSORS": 0
            },
            "house_edge": 0.0  # Fair game, no house edge
        }

    async def _get_gizmo_choice(self, context: SegmentContext) -> str:
        """
        GIZMO makes rock-paper-scissors choice

        Could use SWARM to analyze community betting patterns
        and make "intelligent" choice, or just random for fairness
        """

        # Option 1: Pure random (fair)
        if not self.swarm or random.random() < 0.5:
            return random.choice(["ROCK", "PAPER", "SCISSORS"])

        # Option 2: Ask GIZMO to be strategic
        try:
            # Query GIZMO for choice based on meta/vibes
            query = f"Rock paper scissors choice for show {context.show_id} segment {context.segment_number}. What's the move?"
            result = await self.swarm.query(query, ticker="GAMBA")

            # Extract choice from GIZMO's response
            response = result.get("response", "").upper()

            if "ROCK" in response:
                return "ROCK"
            elif "PAPER" in response:
                return "PAPER"
            elif "SCISSORS" in response:
                return "SCISSORS"
            else:
                return random.choice(["ROCK", "PAPER", "SCISSORS"])

        except Exception as e:
            print(f"Error getting GIZMO's choice: {e}")
            return random.choice(["ROCK", "PAPER", "SCISSORS"])

    def _hash_choice(self, choice: str, show_id: int, segment_number: int) -> str:
        """
        Hash GIZMO's choice for provable fairness

        In production: use proper cryptographic hash
        """
        import hashlib
        data = f"{choice}:{show_id}:{segment_number}".encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def _get_gizmo_taunt(self) -> str:
        """Get random GIZMO trash talk"""
        taunts = [
            "Think you can outsmart the Eye? Let's see what you got, degens! 👁️",
            "Rock, paper, scissors... GIZMO knows all. Do you? 🎲",
            "I've analyzed 10,000 games. You've played... how many? 🤖",
            "My neural nets say ROCK... or do they? 🧠",
            "Feeling lucky, anon? GIZMO never loses... except when I do 😏",
            "The meta is SCISSORS. Or is it? Double reverse psychology activated 🎯",
            "GIZMO's circuits are calculating... probability matrices loading... 💭",
            "You think this is random? Cute. Everything is signal, anon 📊",
            "Retardia says ROCK is the play. Is Retardia ever wrong? (Yes) 👸",
            "GAMBA SZN! Let's get this bread, degenerates! 💰"
        ]
        return random.choice(taunts)

    def _format_gamba_notes(
        self,
        rps_round: Dict,
        gizmo_taunt: str,
        context: SegmentContext
    ) -> str:
        """Format speaker notes for GAMBA RPS segment"""

        betting_window_min = rps_round['betting_window_seconds'] // 60

        return f"""
=== 🎲 GAMBA SEGMENT: ROCK PAPER SCISSORS vs GIZMO 🎲 ===

{gizmo_taunt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 HOW TO PLAY:

1. Pick your move: ROCK 🪨 | PAPER 📄 | SCISSORS ✂️
2. Place your bet (crypto/points)
3. Submit before timer expires
4. GIZMO reveals choice
5. Winners get PAID! 💰

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💵 PAYOUTS:

• BEAT GIZMO → 2x your bet 🏆
• TIE with GIZMO → Get your bet back 🤝
• LOSE to GIZMO → Better luck next time! 💀

(No house edge - this is a fair fight!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BETTING WINDOW: {betting_window_min} MINUTES

Round ID: {rps_round['round_id']}
GIZMO's Choice Hash: {rps_round['gizmo_choice_hash']}
(Proof of pre-commitment - GIZMO can't change after seeing your picks)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 EXAMPLE PLAYS:

You: ROCK 🪨  | GIZMO: SCISSORS ✂️  → YOU WIN! 2x
You: PAPER 📄 | GIZMO: PAPER 📄    → TIE! 1x
You: SCISSORS ✂️ | GIZMO: ROCK 🪨  → GIZMO WINS! 0x

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 CURRENT ROUND STATS:

Total Bets: {rps_round['bet_counts']['ROCK'] + rps_round['bet_counts']['PAPER'] + rps_round['bet_counts']['SCISSORS']}
Pool Size: ${rps_round['total_pool']:.2f}

ROCK 🪨: {rps_round['bet_counts']['ROCK']} bets
PAPER 📄: {rps_round['bet_counts']['PAPER']} bets
SCISSORS ✂️: {rps_round['bet_counts']['SCISSORS']} bets

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 LEADERBOARD (Top degens this show):
1. anon_whale - 5 wins, +$1,420.69
2. paper_hands - 3 wins, +$420.00
3. diamond_degen - 2 wins, +$250.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎲 GAMBA GAMBA GAMBA! 🎲

May the odds be ever in your favor, degens!
(They won't be. GIZMO sees all 👁️)

GET YOUR BETS IN NOW! ⏱️
"""

    async def resolve_round(
        self,
        round_id: str,
        player_bets: List[Dict]
    ) -> Dict:
        """
        Resolve rock-paper-scissors round

        Args:
            round_id: Round identifier
            player_bets: List of {user_id, choice, bet_amount}

        Returns:
            Resolution with winners, payouts, and GIZMO's reveal
        """
        # This would be called at end of segment
        # Placeholder for when integrated with actual betting system

        return {
            "round_id": round_id,
            "status": "resolved",
            "gizmo_choice": "ROCK",  # Revealed
            "gizmo_choice_hash": "abc123...",
            "total_bets": len(player_bets),
            "winners": [],
            "total_payout": 0.0,
            "house_profit": 0.0
        }

    def _determine_winner(self, player_choice: str, gizmo_choice: str) -> str:
        """
        Determine rock-paper-scissors winner

        Returns: "WIN", "LOSS", or "TIE"
        """
        if player_choice == gizmo_choice:
            return "TIE"

        wins = {
            "ROCK": "SCISSORS",
            "PAPER": "ROCK",
            "SCISSORS": "PAPER"
        }

        if wins.get(player_choice) == gizmo_choice:
            return "WIN"
        else:
            return "LOSS"
