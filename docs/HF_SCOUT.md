# Hugging Face scout: what could raise the 4B's pointing accuracy tonight

Written 2026-11-15, about 02:15 EST. Every repo below was returned by the Hugging Face API and its
card (or config) was read before it was described. Scores are the source's own (paper or card), not
ours, unless stated. "Unverified" means I could not confirm it from a card, config or paper text.

The headline: **two full-precision grounding specialists built on exactly Qwen3.5-4B are public**
(same width 2560, same 32 layers, checked in their `config.json`), and one of them ships a
grounding head of the same kind as our decoder. Neither is in our notes so far.

## Ranked experiments (expected gain per GPU-hour, for the 4B)

| # | What to do | Repos | Why it should help, given what we know | GPU time | Main risk |
|---|---|---|---|---|---|
| 1 | Score the two same-size specialists on our 158 cases, pick the better as the 4B teacher | `jcwang0602/Seg2Click-Qwen3.5-4B`, `Hcompany/Holo-3.1-4B` | A teacher with the same layers and width lets us match states layer for layer; our 9B teacher cannot. Seg2Click paper reports 93.1% on ScreenSpot-v2 for this 4B | 0.3 h | Holo's 4B grounding score is only in an image on its card; Seg2Click needs its own inference code |
| 2 | Train multipliers and decoder against the 4B teacher's states (final layer and layer 20), half state-matching, half task loss | winner of 1, `Qwen/Qwen3.5-4B` | RILQ shows that at 2 bits matching the whole model's final output works where per-layer matching does not; our decoder already reads layer 20 well | 4 to 6 h | Teacher states may be too far from what ternary weights can reach; watch the task loss |
| 3 | Lift Seg2Click's rank-16 change out of its merged weights and attach it to Bonsai 4B as a full-precision side path, with its 54M mask head; test as is, then tune multipliers under it | `jcwang0602/Seg2Click-Qwen3.5-4B`, `Qwen/Qwen3.5-4B` | Our own rank-16 paths started from zero on layers 4 to 19 and had 1,500 steps; this one is trained, covers every linear layer in all 32 layers, and comes with a head | 0.5 h to test, 2 h to tune | The change was learned around full-precision weights; may not transfer to ternary ones without step 2 |
| 4 | Add GroundCUA to training (dense desktop boxes, ready-made instructions) | `likaixin/GroundCUA-train` | Desktop, human-verified, 51k screens with about 1.87M instructions; one 20 GB parquet pull; our set is 26k cases | pull 15 min, convert 30 min CPU | Windows and Linux heavy; keep the Mac share of each batch |
| 5 | Give the decoder a finer-than-token output: 32x32 scores per image token by pixel shuffle, trained on the box as a mask | recipe from `jcwang0602/Seg2Click-Qwen3.5-4B` (`phase1_mask_decoder.json`), arXiv 2610.16234 | Our grid-plus-offset head is limited on small targets; this gets pixel precision in the same single image read, no zoom | 2 to 3 h | 54M-parameter head in the source; ours is 25M and reads layer 20, not the last layer |
| 6 | Change the grid target from one cell to a box-shaped soft target, and penalise score mass outside the box | arXiv 2508.13634 (V2P), 2511.00810 (GUI-AIMA), 2506.03143 (GUI-Actor) | Cheap swap in the decoder loss; V2P reports +7.9 on ScreenSpot-Pro over GUI-Actor at 7B, mostly small targets | 1 h per variant | Gain on ScreenSpot-v2 itself was small in the source (+0.3) |
| 7 | Add 674k rewritten ScaleCUA instructions with boxes (annotations only; images are the ScaleCUA ones we are already pulling) | `SnowRainsdy/ScaleCUA_Bbox_Rewrite`, `OpenGVLab/ScaleCUA-Data` | Action-style requests ("click ...") instead of element descriptions, each marked as verified; nearly free once ScaleCUA images are on disk | pull 2 min, convert 20 min CPU | No licence stated on the card; written by another model |
| 8 | For written answers, distil the teacher's token probabilities and weight coordinate tokens 4x | teacher from 1 or `inclusionAI/UI-Venus-2-9B`; method notes from `zcyyyds/Qwen3.5-4B-GUI-Edge`, arXiv 2605.00642, 2606.18101 | Same tokenizer across Qwen3.5 sizes, so token-level targets line up; GUI-Edge card says coordinate tokens are 15% of output but carry 84% of image dependence | 2 to 3 h | Teacher signal goes bad once the student's first digits are off; the 2606.18101 gate handles this |
| 9 | Retry side paths the RILQ way: a low-rank path on every linear layer (recurrent ones included), trained on state-matching to the parent, then on the task | `Qwen/Qwen3.5-4B`, arXiv 2412.01129, 2605.06183 | Our failed attempt was mid layers only with task loss only; RILQ's rank 16 with whole-model loss beat rank 256 with per-layer fitting at 2 bits | 1 h matching, 2 h task | Ternary is harsher than their 2-bit setups; gain unknown |
| 10 | Repeat the UI-Venus weight comparison at 4B: how much of (specialist minus parent) fits into multipliers, write that part in | `Hcompany/Holo-3.1-4B` (and Seg2Click 4B), `Qwen/Qwen3.5-4B` | Worked as analysis at 9B (2.5 of 4 points of norm); here teacher and student are the same size so the change can be written directly | 0.3 h, mostly CPU | Must first check the vision tower is unchanged (it is not in Seg2Click) |
| 11 | Filter the 200k widening by agreement of two or three strong pointers | `inclusionAI/UI-Venus-2-9B`, `PrentisAI/GroundGUI-8B`, `Salesforce/GTA1-7B-2507`, `inclusionAI/UI-Venus-1.5-8B` | OS-Atlas and ScaleCUA boxes are noisy; drop cases where teachers agree with each other and not with the box | 2 to 3 h | Removes hard but correct cases; keep a share of disagreements |
| 12 | Larger pulls if a GPU sits idle on data: synthetic icons, components and layouts; a 633k research-only set | `xlangai/Jedi`, `PrentisAI/ScreenRef`, `PrentisAI/ScreenRef-Annotations` | Icons and small controls are where a 4B loses most | 1 to 2 h of download each | 99 GB and 351 GB; Jedi coordinates are pre-scaled; ScreenRef is academic-research-only and gated |

## Details per experiment

**1. Score the two 4B specialists.** `jcwang0602/Seg2Click-Qwen3.5-4B` (Apache-2.0, 9.3 GB): merged
backbone plus `phase1_mask_decoder.safetensors` (216 MB, float32). Card: "LoRA is already merged";
inference needs the code at github.com/jcwang0602/Seg2Click (`Seg2ClickPredictor.from_pretrained`,
returns a normalised point). The paper (arXiv 2610.16234) reports for the Qwen3.5-4B version 93.1%
ScreenSpot-v2 and 50.2% ScreenSpot-Pro; 0.8B, 2B and 9B versions exist under the same author
(89.9, 91.6, 94.1 on v2). `Hcompany/Holo-3.1-4B` (Apache-2.0, 10.4 GB, 1,690 downloads): config
is `qwen3_5`, hidden 2560, 32 layers, vision 1024 by 24; card lists Qwen3.5-4B among its bases and
says web, desktop and mobile. Its grounding numbers are in an image only, and the card does not say
whether it is a full fine-tune or what coordinate format it writes (read `chat_template.jinja`).
Run both on the 158 cases at 1280 px before trusting either.

**2. State-matching to the 4B teacher.** RILQ (arXiv 2412.01129): loss is the Frobenius distance
between full-precision and quantized outputs of the last layer, weighted 0.5, plus the normal task
loss weighted 0.5; Adam, lr 1e-4, batch 8, up to 10,000 steps with early stop, 256 calibration
sequences of length 512, about 37 minutes on a 7B. They report that matching per linear layer or
per block is what fails at 2 bits. For us: teacher is the winner of experiment 1 run on the same
image and request; match the final layer and, since the decoder reads it, layer 20; trainable parts
are the multipliers and the decoder. The matching target needs no labels, so unlabeled screens work.

**3. Transplant Seg2Click's change.** Its decoder config states 38,993,920 LoRA parameters at
rank 16, alpha 32, dropout 0.05, on all linear layers in vision and language blocks, base frozen,
then merged. So `merged minus Qwen/Qwen3.5-4B` is rank 16 per linear layer up to BF16 rounding; a
truncated SVD at rank 16 recovers it. Attach the language-model part to Bonsai 4B as a
full-precision side path, take the vision tower from the Seg2Click checkpoint as is (its vision
layers were adapted too, so it is not the parent's tower), and load the mask head unchanged. The
head reads the last layer's image-token states joined with the projected vision output
(`LayerNorm(5120)-Linear(5120,2560)-GELU-Linear(2560,2560)`, last linear zero-initialised), is
steered by the state of a fixed action placeholder token, uses two 3x3 conv blocks at 1024
channels, then pixel shuffle by 32. A second ready-made adapter for a zero-cost check:
`zcyyyds/Qwen3.5-4B-GUI-Edge` has `adapter/adapter_model.safetensors` (130 MB; rank 16, alpha 32;
targets `in_proj_qkv, in_proj_z, in_proj_b, in_proj_a, out_proj, q_proj, k_proj, v_proj, o_proj,
gate_proj, up_proj, down_proj`, language model only). It is a phone agent (AndroidControl,
GUI-Odyssey, CAGUI, then reinforcement on GroundCUA) and CC BY-NC 4.0, so a probe, not something
to ship.

**4. GroundCUA.** `likaixin/GroundCUA-train`: MIT, 20.4 GB in 6 parquet files, 51,055 rows, columns
`image_id, image, num_elements, instructions, coords, bboxes, inst_type, software`. Instruction
counts by type on the card sum to about 1.87M (for example 164,702 functional, 97,246 spatial,
80,532 direct text, 8,514 direct icon). Source paper (arXiv 2511.07332): 87 applications, 56K
screenshots, 3.56M human-verified element annotations; their 7B reached 90.4% ScreenSpot-v2 from
700K desktop-only examples. The raw form is `ServiceNow/GroundCUA` (MIT, 21.7 GB, 100,000 small
files: slower to pull). No ScreenSpot overlap is stated on either card.

**5. Finer-than-token output.** From the Seg2Click paper and config: target is the box as a hard
mask; loss 0.5 BCE + 0.5 Dice (smoothing 1); click rule is threshold 0.5, largest 4-connected
blob, its centroid, falling back to the probability-weighted centroid. Training there: one epoch,
39,226 updates, effective batch 32 on eight GPUs, AdamW lr 1e-4, cosine, no warmup, no weight
decay, backbone BF16 and head float32, image pixel bounds 3,136 to 5,720,064. Matched-backbone
gains at 0.8B: +1.0 on ScreenSpot-v2 and +1.5 on Pro over written coordinates; +0.5 and +4.9 over
a reproduced GUI-Actor head. For our decoder: keep the layer-20 input, add the pixel-shuffle
output next to the existing grid-plus-offset output and compare the two on small targets.

**6. Target shape.** GUI-Actor (arXiv 2506.03143): every image token overlapping the box is
positive, uniform, KL between the score softmax and that distribution; a self-attention layer
over image-token states before scoring; head about 20M at 2B. Its head-only variant (backbone
frozen) reached only 73.9 to 74.9% on ScreenSpot-v2 against 88.6 to 89.5% with the backbone
trained, which matches our finding that the multipliers matter. V2P (arXiv 2508.13634): Gaussian
centred on the box with sigma equal to box width and height divided by a factor (1.0 in the main
setup), integrated over each token's footprint, normalised, KL loss; plus a term that sums the
score mass on tokens outside the box; lr 5e-6 with full fine-tune. GUI-AIMA (arXiv 2511.00810):
weight per positive token is its overlap with the box times a Gaussian with spread 0.8 of box
size; 92.1% ScreenSpot-v2 at 3B from about 85k screenshots, lr 5e-6, batch 64, one epoch.

**7. ScaleCUA rewrite.** `SnowRainsdy/ScaleCUA_Bbox_Rewrite`: 1.7 GB, three JSON files, 674,070
samples (99,979 + 99,965 + 474,126). `images` paths are relative to the `OpenGVLab/ScaleCUA-Data`
root (for example `data/data_20250310/ubuntu/files/.../images/step_2.png`); `messages` hold the
instruction and action; coordinates are 0 to 1000 per axis; boxes and verification flags are kept.
Take only rows whose image folders we have already unpacked.

**8. Coordinate-token distillation.** GUI-Edge card: final training stage weights coordinate
tokens 4x. GUI-SD (arXiv 2605.00642): teacher sees the same image with the target box and a soft
mask drawn in, student is trained on the teacher's per-token distribution, weighted by digit
significance and teacher confidence; data at `yankie123/GUI-SD-data` (5.5 GB, 6,990 images, one
`anno.jsonl`, no card). Arxiv 2606.18101 adds a gate: drop the teacher's signal for a token when
the student's digits so far can no longer land inside the box; they report neither the gate nor
the confidence scaling helps alone.

**9. Side paths, retried.** Differences from our failed run: paths on every linear layer
(`in_proj_*`, `out_proj` in the recurrent layers as well as attention and MLP), first trained on
the state-matching loss of experiment 2 against the parent `Qwen/Qwen3.5-4B`, only then on the
task. RILQ numbers at 2 bits: rank 16 with whole-model loss gave perplexity 9.24 where rank 256
fitted per layer gave 9.56; default rank 64. Arxiv 2605.06183 reports that one path on a single
shallow MLP down-projection, found by a gradient-energy probe, beat broad placement with 0.7% of
the parameters; the probe is one backward pass per candidate, cheap to try on Bonsai.

**10. Weight comparison at 4B.** Download only the language-model tensors of the specialist and
the parent; compute per 128-weight group the least-squares multiplier change, write it in, score.
Check vision-tower equality first (Seg2Click's differs by construction; Holo's is unknown).

**11. Agreement filter.** `PrentisAI/GroundGUI-8B` (Apache-2.0, base Qwen3-VL-8B, card: 95.2%
ScreenSpot-v2 as 1211/1272, 63.9% Pro). `Salesforce/GTA1-7B-2507` (Apache-2.0, 16.6 GB).
`inclusionAI/UI-Venus-1.5-8B` (Apache-2.0, 17.5 GB). `ServiceNow/GroundNext-7B-V0` (Apache-2.0,
90.4% v2, desktop-trained). `mPLUG/GUI-Owl-1.5-4B-Instruct` (MIT, 8.9 GB) is a 4B but on Qwen3-VL
(36 layers), so teacher or voter only. `Hcompany/Holo2-4B` (Apache-2.0, Qwen3-VL-4B, card: 93.2%
v2, 57.2% Pro), same remark.

**12. Larger pulls.** `xlangai/Jedi`: Apache-2.0, 99.2 GB, jsonl plus split image archives;
icon, component, layout and refusal sets; the card warns that coordinates were rescaled for a
2,700-token image limit and images must be resized the same way before use. `PrentisAI/ScreenRef`:
351 GB in 447 parquet shards, access granted automatically on accepting terms, licence is
academic research only with no redistribution; 633,369 instructions (267,172 desktop, 303,790
web, 62,407 mobile), columns `image, width, height, conversations, task, conv_style`,
coordinates 0 to 1000; annotations alone are open at `PrentisAI/ScreenRef-Annotations` (0.48 GB)
for picking desktop shards first. `vyokky/GUI-360` (MIT, 574 GB, Windows Office, 1.2M steps) and
`osunlp/UGround-V1-Data-Box` (265 GB, CC BY-NC-SA, gated, web, 757k) are too large for tonight.

## Things that must not go into training

- Benchmarks under other names: `OS-Copilot/ScreenSpot-v2`, `likaixin/ScreenSpot-Pro`,
  `bevaya/ScreenSpot`, `Voxel51/ScreenSpot*`, `HongxinLi/ScreenSpot_v2`, `KevinQHLin/ScreenSpot`,
  `TIGER-Lab/ScreenSpot-Pro`, `lmms-lab/ScreenSpot-Pro`.
- `HyperCluster/OS-Atlas_ScreenSpot` (106,520 rows, no card): the name says ScreenSpot; skip.
- `axel-darmouni/qwen35-4b-screenspot-lora` (rank 16 on Qwen3.5-4B, vision layers included, no
  licence, template card): the name says it was trained on ScreenSpot; do not use as a teacher.
- `agentsea/wave-ui-25k` (10.6 GB, 24,978 rows, `image, instruction, bbox, source, platform`):
  one of its three sources is `agent-studio/GroundUI-18K`; whether that contains ScreenSpot
  screens is unverified, so filter on the `source` column or skip. GUI-Actor, Seg2Click and
  GUI-AIMA all trained on Wave-UI, so the same doubt applies to their reported v2 scores.
- `mlfoundations-cua-dev/easyr1-*` sets mix in `ServiceNow/ui-vision`, itself a benchmark.

## Small element detectors (for the later snapping stage only)

- `microsoft/OmniParser-v2.0`: MIT repo, 1.4 GB; the original `icon_detect` weights are AGPL-3.0
  (YOLOv8), the card says a newer `icon_detect_v3/model.pt` (YOLOv9-E) is MIT.
- `macpaw-research/yolov11l-ui-elements-detection`: AGPL-3.0, 0.1 GB, macOS UI elements
  (arXiv 2507.16704, the Screen2AX work).
- `Navanjana/yolo-GroundCUA`: a dataset in detector format built from GroundCUA (not read).

## Looked for, not found

- **A LoRA for Qwen3.5-4B trained for desktop pointing that we can download now.** The closest,
  `mdabis/qwen35-gui-grounding`, `_v2`, `_v3` (Apache-2.0, adapters of 65, 130 and 310 MB, trained
  on about 23.5K samples from `showlab/ShowUI-desktop`, `zonghanHZH/UGround-V1-8k`,
  `zonghanHZH/AMEX-8k`), are behind manual access approval. Their card reports 92.5, 93.4 and
  92.7% on ScreenSpot-v2 (v3 unfroze the vision tower and got worse). Rank and target modules are
  not on the card. Worth an access request, but not for tonight.
- **Any ternary or Bonsai model tuned for screens.** `prism-ml` hosts only GGUF and MLX builds;
  nothing GUI-related derives from them.
- **Published results for add-on parameters on ternary or BitNet-style language models with
  accuracy numbers.** Only vendor and community write-ups (frozen ternary base, FP16 rank-8
  paths, applied at run time, not merged). RILQ at 2 bits is the nearest evidence with numbers.
- **Region-then-point in one image read as a published method.** The zoom papers found
  (arXiv 2604.14113, 2603.17441, 2610.33645, GUI-AIMA's zoom step) all read a crop a second time.
  Seg2Click's finer output is the single-read alternative.
- **A verifier that needs no second image read.** GUI-Actor's (`microsoft/GUI-Actor-Verifier-2B`)
  re-reads the image with the candidate marked; it added 0.7 to 1.4 points on ScreenSpot-v2.
- **Grounding scores for `Hcompany/Holo-3.1-4B` in text**, and its training recipe.
- **Other Qwen3.5-4B computer-use fine-tunes with pointing scores above ours.** Found but weaker
  or off-target: `GUIAgentt/qwen35-4b-3mfinal-succed-c2lg-3ep` (web agent, card: 80.9%
  ScreenSpot-v2, manual gate), `OnAnOrange/CUA-Lite-Qwen3.5-4B-ScaleCUA-gpt5_5-epoch3-public`
  (Apache-2.0, full fine-tune on 5,000 desktop trajectories, lr 5e-6, no pointing score),
  `inclusionAI/ZoomGain-4B` (Qwen3.5-4B tuned for fine detail in natural images, arXiv 2611.14076,
  no licence stated, not a GUI model), `dongjintao/GUI-Swift-4B` (adapter on GUI-Owl-1.5-4B, not
  our parent).
