# Milestone 9 — Learned Fingering Ranker (v0.9)

AutoTab can now learn a lightweight preference model from the correction history created in Milestone 8.

## Model

The baseline is intentionally small and interpretable: a pairwise linear ranker trained with logistic preference learning.

Each correction means:

```text
corrected position > original predicted position
```

The model learns weights over position-level features:

- normalized fret
- normalized string index
- open-string flag
- high-fret penalty region
- distance from middle strings
- pitch class
- capo
- bias

No external ML dependency is required for this baseline.

## How it is used

The deterministic fingering engine still generates only physically legal voicings. The learned ranker never creates candidates.

For each legal candidate:

```text
total cost
  = heuristic playability cost
  + transition cost
  + learned preference cost × strength
```

This preserves the hard constraints developed in earlier milestones while allowing human corrections to influence ranking.

## Safety / fallback

If no model exists, or the trained model contains zero useful examples, AutoTab uses the deterministic fingering engine unchanged.

The learned component is therefore optional and reversible.

## API

`POST /ranker/train`

Trains/retrains the global baseline ranker from the current correction dataset and persists it as:

`artifacts/models/fingering_ranker.json`

`GET /ranker/status`

Returns model version, feature names, example count and weights.

Retune requests now accept:

```json
{
  "use_learned_ranker": true,
  "ranker_strength": 0.55
}
```

## Product controls

The practice player includes:

- enable/disable learned ranker
- learned-ranker strength slider
- training-example count
- Train / refresh ranker action

## Current limitations

The model is global and position-level. It does not yet model:
- chord identity
- previous/next fingering
- tempo
- techniques
- genre/style
- user identity
- hand size
- entire voicing features
- validation/generalization metrics

Those become valuable once the correction dataset grows.
