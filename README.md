# Hyper-Threat Tokencast

**9-segment rotating cryptocurrency live show orchestration system**

Integrates pump.fun token launch monitoring, SWARM market intelligence, and automated segment transitions for live crypto content shows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  DEX APIs (Birdeye, Dexscreener)  │  Social (Twitter, Telegram) │
│  - OHLCV                          │  - Tweets/mentions           │
│  - Holder data                    │  - Engagement metrics        │
│  - Transaction flow               │  - Influencer signals        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE ENGINEERING                          │
├─────────────────────────────────────────────────────────────────┤
│  Price Features:          │  Social Features:                    │
│  - Volume ratio           │  - Mention velocity                  │
│  - Price momentum         │  - Sentiment score                   │
│  - PV divergence          │  - Influencer ratio                  │
│  - ATH distance           │  - Narrative coherence               │
│  - Trend strength         │  - Meta signals (cult, hype scores)  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│        HMM MODEL         │    │       NLP MODEL          │
├──────────────────────────┤    ├──────────────────────────┤
│  States:                 │    │  Phases:                 │
│  0. Accumulation         │    │  0. Discovery            │
│  1. Breakout             │    │  1. Validation           │
│  2. Euphoria             │    │  2. Peak                 │
│  3. Distribution         │    │  3. Doubt                │
│  4. Dead                 │    │  4. Dead                 │
│                          │    │                          │
│  Output:                 │    │  Output:                 │
│  - State probabilities   │    │  - Phase probabilities   │
│  - Transition probs      │    │  - Sentiment             │
│  - Regime stability      │    │  - Narrative strength    │
└──────────────────────────┘    └──────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SIGNAL FUSION                               │
├─────────────────────────────────────────────────────────────────┤
│  Divergence Detection:                                           │
│  - Narrative leads price → EARLY ENTRY opportunity               │
│  - Price leads narrative → EXIT opportunity                      │
│                                                                  │
│  Signals: STRONG_LONG, LONG, HOLD, REDUCE, SHORT, STRONG_SHORT  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Installation

```bash
# Clone
git clone <repo>
cd memecoin_ml

# Create environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set API keys in config/settings.py
```

---

## Quick Start

### 1. Analyze a Token

```python
from main import MemecoinAnalyzer
import asyncio

analyzer = MemecoinAnalyzer()

result = asyncio.run(analyzer.analyze_token(
    token_address="YOUR_TOKEN_ADDRESS",
    ticker="TICKER"
))

print(f"Signal: {result['signal']}")
print(f"Regime: {result['hmm_regime']}")
print(f"Phase: {result['nlp_phase']}")
print(f"Divergence: {result['regime_narrative_divergence']}")
```

### 2. Train Models

```bash
# First, label your data (see labeling/LABELING_STRATEGY.md)

# Then train
python main.py --mode train \
    --training-data data/labels/training.npz \
    --model-path models/saved/hmm_v1.pkl
```

### 3. Run Live Monitor

```python
from main import MemecoinAnalyzer, LiveMonitor
import asyncio

analyzer = MemecoinAnalyzer(hmm_model_path="models/saved/hmm_v1.pkl")
monitor = LiveMonitor(analyzer)

# Add tokens to watch
monitor.add_token(
    address="...",
    ticker="EXAMPLE",
    alert_config={
        "divergence_threshold": 0.3,
        "min_confidence": 0.6
    }
)

# Run
asyncio.run(monitor.run_scan())
```

---

## The Models

### Hidden Markov Model (HMM)

Detects market regimes from price/volume data. Key insight: market states are "hidden" - you can't directly observe "we're in distribution phase" but you can observe emissions (price action, volume, holder behavior) that probabilistically correspond to hidden states.

**States:**
- **Accumulation**: Smart money loading quietly. Low volume, ranging price.
- **Breakout**: Meta forming. Volume spike, price momentum, narrative building.
- **Euphoria**: Peak tautology. "Up only" feeling, max FOMO.
- **Distribution**: Smart money exiting. Volume still high, price making lower highs.
- **Dead**: Capitulation complete. Minimal activity.

**Transition Matrix:**
```
          acc   brk   eup   dis   dead
acc     [ 0.7   0.2   0.0   0.05  0.05]
brk     [ 0.1   0.5   0.3   0.1   0.0 ]
eup     [ 0.0   0.05  0.4   0.5   0.05]
dis     [ 0.1   0.0   0.05  0.4   0.45]
dead    [ 0.15  0.05  0.0   0.0   0.8 ]
```

### NLP Pipeline

Detects narrative phases from social media. The narrative typically LEADS price action.

**Phases:**
- **Discovery**: "Found this gem, no one talking about it"
- **Validation**: "Told you, LFG, it's happening"  
- **Peak**: "Never selling, diamond hands, life changing"
- **Doubt**: "Why dump, paper hands, manipulation"
- **Dead**: "It's over, lesson learned, rugged"

**Features:**
- Sentiment tuned for CT language
- Narrative clustering via embeddings
- Meta signal extraction (cult score, hype score)
- Influencer sentiment weighting

### Signal Fusion

The alpha is in the divergence:

| Narrative | Price | Signal |
|-----------|-------|--------|
| Validation | Accumulation | EARLY LONG - narrative forming before price |
| Peak | Breakout | LONG - confluence confirmation |
| Peak | Distribution | EXIT - smart money leaving while retail bullish |
| Discovery | Dead | Potential resurrection watch |

---

## Labeling Data

See `labeling/LABELING_STRATEGY.md` for complete methodology.

**Key principles:**
1. Label transitions, not just states
2. Validate with both quantitative heuristics and visual inspection
3. Preserve narrative-price divergences as features (not errors)
4. Cross-validate HMM and NLP labels

---

## File Structure

```
memecoin_ml/
├── config/
│   └── settings.py          # Configuration and parameters
├── data/
│   └── pipeline.py          # Data collection and feature engineering
├── models/
│   ├── hmm.py              # Hidden Markov Model
│   ├── nlp.py              # NLP narrative detection
│   └── fusion.py           # Signal fusion layer
├── labeling/
│   ├── LABELING_STRATEGY.md # Complete labeling methodology
│   └── labeler.py          # Auto-labeling and validation tools
├── main.py                  # Entry point and orchestrator
└── requirements.txt
```

---

## API Keys Required

- **Twitter/X**: For social data (bearer token)
- **Birdeye**: For Solana DEX data
- **DexScreener**: Free tier works for basic data

---

## Limitations

1. **Data lag**: Social APIs have rate limits; real-time is approximate
2. **Regime detection lag**: HMM inherently lags (needs observations)
3. **Overfitting risk**: Memecoins have fat tails; train on diverse data
4. **Exogenous shocks**: Elon tweets, listings, rugs - can't predict

---

## Contributing

1. Label more data (most valuable contribution)
2. Improve CT sentiment lexicon
3. Add data sources (Discord, Telegram)
4. Better transition priors from domain knowledge

---

## License

MIT
