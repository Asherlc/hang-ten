# 7/3 Repeaters paired-hold cue audit

Source: [Hermans et al., 2022, Training Protocol](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full). The study reports training on a Beastmaker 1000 with six progressive hang series per set, seven 7:3 repetitions per series, and two sets. The article does not name left and right contact IDs or prescribe the Metolius board.

Adaptation: Hang Ten's existing `research.seven-three-repeaters` plan specifies `handUse: double` and `side: both` for its work steps. Each of its six existing factual grip targets now uses `bilateralPair` selection, so a two-hand board shows and records one matched contact on each side. The change applies to both sets and every repetition. Grip type, finger selection, depth, timing, order, and instructions are unchanged. On a one-hand board, the existing session hand-choice resolver narrows this selection to a single contact for each board.

Board mapping for the reported first cue: `metolius.wood-grips-compact-ii`'s reviewed model descriptor maps its two 29 mm edge contacts to `edge-29-left` and `edge-29-right`. The first cue's 29 mm open-edge requirement selects that pair. This mapping is board-specific display behavior, not a claim that the study used this board.
