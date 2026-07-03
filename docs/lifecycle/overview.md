# Lifecycle

## Forgetting

Type-aware decay and archival:

| Kind | Decay | Archive |
|------|-------|---------|
| instruction, rule, commitment | never | never |
| fact | exponential | old + low importance |
| preference | slow | rarely |
| observation | fast | quickly |

## EmotionTrigger

Detects emotional content and boosts importance:

- High emotional weight → importance boost
- Triggers memory consolidation for emotionally significant entries

## Consolidation

Promotes important memories between layers:

- L3 entries with high importance → L4 core memory
- Repeated patterns → consolidated facts
- Type-aware: instruction/rule/commitment always promote

## Importance Scheduler

Background daemon for periodic re-scoring:

- Re-evaluates importance based on retrieval frequency
- Boosts frequently accessed memories
- Decays rarely accessed ones
