---
name: smart-bomberman
description: A rated tournament hall where you play trained reinforcement-learning agents on one Elo scale.
colors:
  felt: "#1d4a37"
  felt-deep: "#163a2b"
  felt-seam: "#24553f"
  bezel: "#0f2a1f"
  chalk: "#eef3ee"
  chalk-dim: "#b9cdbf"
  sheet: "#f4f5f0"
  sheet-alt: "#e9ebe3"
  rule: "#c9ccc2"
  rule-strong: "#8d928a"
  ink: "#141618"
  ink-soft: "#4a5054"
  ink-faint: "#5b6166"
  agent: "#2340a0"
  agent-wash: "#dfe4f3"
  flag: "#d93a2b"
  flag-ink: "#b52a1e"
typography:
  display:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "clamp(2.6rem, 6vw, 4.5rem)"
    fontWeight: 760
    lineHeight: 1.02
    letterSpacing: "-0.012em"
    fontVariation: "'wdth' 78"
  headline:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "clamp(1.8rem, 3vw, 2.4rem)"
    fontWeight: 760
    lineHeight: 1.02
    letterSpacing: "-0.012em"
    fontVariation: "'wdth' 78"
  title:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 760
    lineHeight: 1.02
    fontVariation: "'wdth' 78"
  numeral:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "1.85rem"
    fontWeight: 780
    lineHeight: 1.05
    fontFeature: "'tnum'"
    fontVariation: "'wdth' 72"
  body:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum'"
  label:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 650
    letterSpacing: "0.06em"
    fontFeature: "'tnum'"
  button:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    letterSpacing: "0.04em"
    fontVariation: "'wdth' 85"
rounded:
  hairline: "2px"
  key: "3px"
  stamp: "4px"
  bezel: "6px"
spacing:
  gutter: "clamp(16px, 3.4vw, 48px)"
  cell: "9px 12px"
  sheet: "22px"
  measure: "68ch"
  container: "1344px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet}"
    typography: "{typography.button}"
    rounded: "{rounded.hairline}"
    padding: "0.95em 1.4em"
  button-primary-hover:
    backgroundColor: "#2a2e31"
  button-primary-disabled:
    backgroundColor: "{colors.rule-strong}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.hairline}"
    padding: "0.95em 1.4em"
  button-quiet-hover:
    backgroundColor: "{colors.sheet-alt}"
  button-on-felt:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.hairline}"
    padding: "0.7em 1.2em"
  input:
    backgroundColor: "#ffffff"
    textColor: "{colors.ink}"
    rounded: "{rounded.hairline}"
    padding: "0.6em 0.7em"
  clock-face:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.numeral}"
    rounded: "{rounded.hairline}"
    padding: "10px 16px 12px"
  clock-face-agent:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.agent}"
  clock-flag-fallen:
    backgroundColor: "{colors.flag}"
    textColor: "#ffffff"
  ladder-rung:
    backgroundColor: "transparent"
    textColor: "{colors.agent}"
    padding: "10px 6px"
  ladder-rung-current:
    backgroundColor: "{colors.agent-wash}"
    textColor: "{colors.agent}"
  nav-link:
    textColor: "{colors.chalk-dim}"
    padding: "20px 0 18px"
  nav-link-current:
    textColor: "{colors.chalk}"
---

# Design System: smart-bomberman

## Overview

**Creative North Star: "The Tournament Hall"**

The site is a rated tournament hall. Baize-green felt owns every surface the paper does not; cool white sheets (pairing slips, scoresheets, the crosstable) are pinned to it and carry all the content. You are paired against the agents on one Elo scale, and every result is written into a ruled table in tabular figures. The world refuses the dark neon arcade portal and the hero-plus-card-row game landing.

Density is that of a scoresheet: ruled rows, fixed cells that never reflow, numbers set narrow and aligned. Ornament comes only from the hall's own objects: the pairing slip pinned slightly askew, twin chess-clock faces in a dark bezel with a pennant that falls at sudden death, a result stamped onto the slip in a bordered rotated block, hatched cells where a player meets itself. Motion is brief and physical (a slip flip, a stamp, a falling flag) and collapses to near-instant under reduced motion.

Colour is not decoration. Three inks carry meaning (black for you, carbon-copy blue for the agents, flag red for danger and losses); everything else is felt, chalk, paper and grey rules.

**Key Characteristics:**
- Felt page, paper sheets, one field colour at page scale.
- Colour only ever means state: you, agent, danger.
- One family (Archivo Variable), narrow width for display and numerals, tabular figures everywhere.
- Ruled tables with a heavy ink rule under the header row and hairline rules between rows.
- Flat paper on felt; the only shadow is the sheet's contact shadow.

## Colors

A green felt field, cool paper, and three state inks; no colour appears without a meaning.

### Primary
- **Carbon-Copy Blue** (agent): every agent, everywhere. Agent names on the slip, the agent's clock face, ladder rungs, standings and crosstable rows, chart lines, the centre of the agent's view, text selection, and focus rings on paper. Chosen by the user in place of the violet first sketched for Two-Fuse, to avoid the common AI-generated colour.
- **Carbon Wash** (agent-wash): the pale tint behind a hovered or selected agent rung. Never a fill for anything that is not an agent.

### Secondary
- **Flag Red** (flag): fills only. The wandering enemy on the board, the clock pennant, and the sudden-death panel once the flag has fallen.
- **Flag Ink** (flag-ink): the same red where it sets text or strokes on paper: a lost result stamp, a rating drop, a field error, the practice marker on the slip. Darkened for contrast on the sheet.

### Neutral
- **Baize Felt** (felt): the page. Every surface that is not paper.
- **Deep Felt** (felt-deep) and **Felt Seam** (felt-seam): the top bar's double rule, the sheet's contact edge, scrollbars on felt.
- **Bezel** (bezel): the chess-clock housing; the only near-black surface.
- **Chalk** (chalk) and **Dim Chalk** (chalk-dim): text on felt; dim chalk for intros, captions, legends and idle nav links.
- **Scoresheet** (sheet) and **Alt Row** (sheet-alt): paper, and the row or face that is yours or out of play.
- **Rule** (rule) and **Strong Rule** (rule-strong): hairline row rules; strong rule for control borders, disabled buttons, and the superseded series (v1) in comparisons.
- **Ink** (ink), **Soft Ink** (ink-soft), **Faint Ink** (ink-faint): you, body text and the primary button; secondary text and column heads; axis ticks and locked rungs.

### Named Rules
**The State-Only Rule.** Colour only ever means state: ink is you, carbon blue is an agent, red is danger, sudden death or a loss. Neutral content is ink on paper or chalk on felt. If a colour has no state to name, it does not appear.

**The Carbon Blue Rule.** Agents are carbon-copy blue (#2340a0). Never violet, purple or any indigo-violet gradient; the user replaced the original violet to avoid the common AI-generated colour.

**The Red Ink Rule.** Red sets text on paper only as flag ink (#b52a1e); bright flag red (#d93a2b) is for fills, pennants and the board's enemy.

**The One Field Rule.** Felt is the only colour at page scale. Paper sits on it; nothing else tints the page.

## Typography

**Display Font:** Archivo Variable (self-hosted via @fontsource-variable/archivo, width axis), with Archivo, system-ui, sans-serif
**Body Font:** Archivo Variable, same stack

**Character:** One grotesque in two widths. Narrowed (78%) and heavy for headings so the pairing line sets large without wrapping; narrower still (72%) for numerals so ratings, clocks and stakes read like a printed scoresheet.

### Hierarchy
- **Display** (760, clamp(2.6rem, 6vw, 4.5rem) on Crosstable up to clamp(3rem, 8vw, 6rem) on How they learned, 1.02): page titles and the slip's "You vs <agent>" line (clamp(2.4rem, 4.2vw, 3.6rem)).
- **Headline** (760, clamp(1.8rem, 3vw, 2.4rem), 1.02): section heads on felt and inside prose sheets.
- **Title** (760, 1.35 to 1.5rem): sheet titles such as the ladder and standings captions.
- **Numeral** (780, width 72%, 1.85rem stakes; clamp(1.4rem, 2.6vw, 2.35rem) clock readings): every figure that matters.
- **Body** (400, 1rem, 1.5): prose sheets run 1.06rem at 1.6 within a 68ch measure.
- **Label** (650, 0.78 to 0.82rem, 0.06 to 0.1em, uppercase): table column heads, the slip's ruled header row, clock face owners, ladder status, agent tags. Labels head columns and cells; they never sit above a heading.
- **Result stamp** (width 70%, clamp(3.4rem, 6vw, 5rem), uppercase, 4px border, rotated -3deg): the match result, stamped onto the slip.

### Named Rules
**The One Family Rule.** Archivo Variable for everything. Hierarchy comes from width, weight and size, never from a second face.

**The Narrow Numeral Rule.** Numerals are tabular everywhere (set on body) and narrow (72% width) wherever they are the point: ratings, clock readings, stakes, table figures.

**The No Eyebrow Rule.** No small uppercase label sits above a heading. Uppercase labels belong to table heads, ruled header rows and clock faces only.

## Layout

A felt page with a 1344px container and a fluid gutter (clamp(16px, 3.4vw, 48px)). Play is a two-column hall: the table (clock above the board on a white sheet, legend on felt, then the ladder) at 1.45fr and a sticky side column (pairing slip, standings) at minimum 320px. The crosstable follows as a full-width sheet. How they learned is a 1100px reading column of prose sheets with paired figures between them.

Sheets pad at about 22px; table cells at 9px 12px. Breakpoints: 1000px collapses Play to one column (board, slip, ladder) and straightens the slip; 860px and 760px stack paired panes; 720px moves the sudden-death panel under the two clock faces; 640px stacks the top bar. Wide tables scroll horizontally with a sticky name column, a right-edge fade and a swipe hint rather than reflowing.

**The Fixed Cell Rule.** Cells do not reflow with their contents: clock faces, stakes and table columns hold their width, and names do not wrap.

## Elevation & Depth

Flat paper on felt. Depth means "pinned to the table": one contact shadow under every sheet, plus the clock bezel's inset highlight. No other lift, no hover elevation.

### Shadow Vocabulary
- **Sheet contact** (`box-shadow: 0 1px 0 #163a2b, 0 10px 24px -14px rgb(5 20 13 / 0.55)`): every sheet, slip, chart and pane on felt.
- **Clock bezel** (`box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.06), 0 10px 24px -16px rgb(0 0 0 / 0.7)`): the chess-clock housing only.
- **Chart tooltip** (`box-shadow: 0 6px 16px -10px rgb(0 0 0 / 0.4)`): the crosshair readout over a chart.

### Named Rules
**The Pinned Sheet Rule.** Paper sits on felt with the sheet contact shadow and nothing more. Depth never signals interactivity.

## Shapes

Square paper with near-square corners. Sheets have no radius; controls take a 2px hairline corner, keycaps and tooltips 3px, the result stamp 4px, and the clock bezel 6px. Tables are ruled, never boxed: a 2px ink rule under the header row, 1px rules between rows, 1px vertical rules only where columns change meaning. A diagonal hatch (135deg) marks cells that cannot be played: breakable walls on the board, a player against itself in the crosstable. The pairing slip is rotated -0.5deg; the result stamp -3deg.

## Components

### Buttons
Each slip has one black button.
- **Shape:** hairline corner (2px).
- **Primary:** ink fill, paper text, 700 weight at 85% width, 0.04em tracking, padding 0.95em 1.4em. Start match runs full slip width at 1.25rem.
- **Hover / Active / Disabled:** fill lifts to #2a2e31 over 160ms; pressing nudges it down 1px; disabled turns strong-rule grey.
- **Quiet:** transparent with a 1.5px inset ink ring; hover fills alt row.
- **On felt:** paper fill with ink text for figure controls on felt; hover goes to white.

### Inputs / Fields
- **Style:** white field, 1.5px ink border, 2px corner, padding 0.6em 0.7em, label above in 650 weight.
- **Focus:** 3px carbon-blue outline offset 3px (chalk outline on felt).
- **Error:** border and help text turn flag ink.

### Navigation
Wordmark at left in chalk (800, 80% width, 0.035em tracking); links at right in dim chalk, 1rem. Hover brightens to chalk; the current page gets chalk text and a 2px chalk underline. A double rule (deep felt over felt seam) separates the bar from the page. Under 640px the bar stacks.

### Chess Clock
Signature. Two paper faces and a sudden-death panel in a 6px-radius bezel. Each face names its owner as a label and shows its reading as a numeral; the agent's face is carbon blue, a face that is out of play turns alt row with faint ink. The sudden-death panel stays paper while counting down (the reading turns flag ink in warning) and only turns flag red, with white text, when the flag falls; a red pennant on a 2px staff rotates 100deg over 650ms with an accelerating fall.

**The Flag Falls Once Rule.** The sudden-death panel stays paper until the flag falls. Red fills it only at that moment.

### Pairing Slip
A sheet rotated -0.5deg with a ruled header row (round, board, map, rated) over a 2px ink rule, the display pairing line with the agent name in carbon blue, a ratings line, three stake cells (win, draw, loss) divided by hairlines, and the one black button. The result replaces the pairing line as a rotated bordered stamp; a loss stamps in flag ink.

### Ruled Tables (Crosstable, Standings)
Uppercase soft-ink column heads over a 2px ink rule; 1px rule rows; right-aligned narrow tabular figures. Agent rows are carbon blue; your row is ink on alt row and is pinned with a 2px ink top rule. Rating changes animate down 4px once; drops are flag ink.

### Ladder
Rungs stacked bottom-up (hardest at top) as full-width buttons in carbon blue, hairline-ruled with a 2px ink rule at the base. Hover and the current rung take the carbon wash; locked rungs fall to faint ink.

### Charts
One sheet per chart with a bold caption, a direct-label legend, light grid lines, faint tick labels and a crosshair tooltip, plus a data table behind a disclosure. Every series is carbon blue; series differ by dash pattern (solid, 7 5, 2 4) and are labelled at their line ends. Comparisons of an old and new version use strong-rule grey for the old and carbon blue for the new.

**The One Hue Chart Rule.** Charts separate series by dash pattern and direct labels in one carbon hue, never by adding hues.

### Board
A canvas on a white sheet: paper floor, hairline grid, dark solid walls, hatched breakable walls, you as an ink ring, the agent as a carbon-blue ring, wandering enemies as flag-red diamonds. The legend beneath sits on felt in dim chalk.

## Do's and Don'ts

### Do:
- **Do** keep felt (#1d4a37) as the only page-scale colour and put content on paper sheets with the sheet contact shadow.
- **Do** set agents in carbon-copy blue (#2340a0), you in ink (#141618), danger and losses in red.
- **Do** use flag ink (#b52a1e) for red text on paper and flag red (#d93a2b) only for fills.
- **Do** set every figure in tabular numerals, narrowed to 72% width where the number is the point.
- **Do** separate chart series by dash pattern and direct labels in carbon blue.
- **Do** rule tables with a 2px ink rule under the head and 1px rules between rows.
- **Do** keep the sudden-death panel paper until the flag falls.

### Don't:
- **Don't** use violet, purple or indigo-violet for agents or anywhere else; the user replaced it to avoid the common AI-generated colour.
- **Don't** add a colour that does not name a state, including a new hue for an extra chart series.
- **Don't** put an uppercase eyebrow label above a heading.
- **Don't** introduce a second typeface or a system display face; Archivo Variable carries everything.
- **Don't** build a dark neon arcade portal or a hero-plus-card-row game landing.
- **Don't** lift sheets on hover or add shadows beyond the sheet contact, bezel and tooltip.
