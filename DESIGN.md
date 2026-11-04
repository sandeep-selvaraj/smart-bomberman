---
name: smart-bomberman
description: The game itself on the web; pick a character from the roster, fight the trained agents in the original arena, and earn an Elo on their scale.
colors:
  you: "#f2b51d"
  danger: "#ff5a5a"
  fuse: "#ff8a1f"
  camper: "#5fb36a"
  wanderer: "#3fc9b8"
  heuristic: "#c4ccd4"
  two-fuse: "#ece6d6"
  two-fuse-hard: "#ff6a5a"
  spark: "#ff7a1a"
  hud-navy: "#1e1e28"
  hud-deep: "#14141c"
  panel: "#2a2a37"
  panel-raised: "#333345"
  frame: "#0c0c12"
  line: "#46465c"
  text: "#f4f4f6"
  text-dim: "#b7b7c9"
  text-faint: "#9a9ab0"
  floor: "#808080"
  floor-light: "#838383"
  floor-dark: "#7b7b7b"
typography:
  display:
    fontFamily: "Silkscreen, monospace"
    fontSize: "clamp(2rem, 5.6vw, 4.2rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0"
  headline:
    fontFamily: "Silkscreen, monospace"
    fontSize: "clamp(1.3rem, 2.2vw, 1.75rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0"
  title:
    fontFamily: "Silkscreen, monospace"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0"
  body:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Silkscreen, monospace"
    fontSize: "0.78rem"
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "0.06em"
  table-head:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 650
    letterSpacing: "0.06em"
rounded:
  tile: "3px"
  panel: "4px"
spacing:
  gutter: "clamp(16px, 3.4vw, 48px)"
  measure: "68ch"
  frame: "3px"
  stack-sm: "12px"
  stack-md: "18px"
components:
  button-primary:
    backgroundColor: "{colors.you}"
    textColor: "{colors.hud-deep}"
    typography: "{typography.title}"
    rounded: "{rounded.panel}"
    padding: "0.75em 1.3em"
  button-primary-disabled:
    backgroundColor: "{colors.line}"
    textColor: "{colors.text-dim}"
  button-quiet:
    backgroundColor: "{colors.panel-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "0.75em 1.3em"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
  hud-bar:
    backgroundColor: "{colors.hud-deep}"
    height: "64px"
  input:
    backgroundColor: "{colors.hud-deep}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "0.6em 0.7em"
  roster-card:
    backgroundColor: "{colors.panel-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "12px 8px"
  roster-card-current:
    backgroundColor: "#3a3a2c"
  sudden-death-banner:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.hud-deep}"
    rounded: "{rounded.tile}"
---

# Design System: smart-bomberman

## Overview

**Creative North Star: "The Game, Unframed"**

The site is the actual game, not a page about it. The page is the original pygame HUD bar's navy; the arena keeps the original grey checker floor and the repo's own generic wall, brick, stone, bomb and explosion sprites, drawn pixel-crisp; the opponents are original 16x16 characters picked from a character-select roster. Everything around the arena borrows the vocabulary of a game menu: bevelled panels in a dark frame, a yellow action button, pixel lettering for the game's own words, a VS card, a HUD that flips red for sudden death.

Density is game-HUD dense on Play and reading-comfortable on How they learned. Pixel lettering is reserved for words the game would say (names, ratings, timers, buttons, section titles); everything a person reads at length is set in a plain sans. The confirmed rejections are the earlier tournament-table world (felt, chalk, score sheets: the site must not look like a chess table) and any reuse of the Bomberman franchise's characters, balloon enemies or title art.

**Key Characteristics:**
- HUD navy page, grey checker arena, original tile sprites at crisp pixel scale.
- Original characters, each with one signature colour that its name wears everywhere.
- Yellow belongs to you; red means danger and sudden death.
- Bevelled game-menu panels in a 3px near-black frame.
- Silkscreen for the game's words, Archivo for reading.

## Colors

A dark HUD navy field with one owner colour (yellow), one alarm colour (red), and a cast of character signature colours; neutrals are cool navies and greys.

### Primary
- **Your Jacket Yellow** (you): the player's colour. The primary button, your name in the HUD, VS card, standings and crosstable, the wordmark, the current-page nav underline, rating gains, the countdown digits, focus rings and text selection. The "you" character's jacket is drawn in it.

### Secondary
- **HUD Alarm Red** (danger): the original HUD's SUDDEN DEATH red. The sudden-death banner, the countdown when it warns, VS lettering, losses and rating drops, practice-match markers, invalid inputs and errors. The arena tints closing cells and dangerous squares with a translucent red (rgba(255, 60, 60, 0.15-0.65)) and marks a fallen fighter with a red cross.
- **Lit Fuse Orange** (fuse): the HUD status when a fighter's bomb is lit.

### Tertiary: character signatures
- **Camper Green** (camper), **Wanderer Teal** (wanderer), **Heuristic Steel** (heuristic), **Two-Fuse Bone** (two-fuse), **Two-Fuse Hard Red** (two-fuse-hard), **Spark Orange** (spark): each agent's name is drawn in its character's signature colour wherever it appears (HUD, VS card, roster, standings, crosstable). The source of truth is `SIGNATURE` in web/src/art/sprites.ts, mirrored as custom properties in global.css. Two-Fuse Bone is also the single hue of the training charts.

### Neutral
- **HUD Navy** (hud-navy): the page, taken from the pygame HUD bar (30, 30, 40).
- **HUD Deep** (hud-deep): the top bar, the match HUD strip, the stakes strip, inputs, and text on yellow and red fills.
- **Menu Panel** (panel) and **Raised Panel** (panel-raised): panel fills; raised for quiet buttons, roster cards, keycaps and your highlighted table row.
- **Frame Black** (frame): every panel, button, arena and input frame, and heavy rules under headers.
- **Line** (line): hairline table rules, dividers, disabled button fill.
- **Text / Text Dim / Text Faint**: primary copy, secondary copy and labels, locked and tertiary states.
- **Arena Floor** (floor, floor-light, floor-dark): the original grey floor, drawn on canvas as a checker of floor-light and floor-dark; floor itself backs the arena frame and HUD bomb chips.

### Named Rules
**The Yours Is Yellow Rule.** Yellow marks the player and the player's actions only. No agent, chart series or decoration wears it.

**The Signature Rule.** An agent's name always wears its character's signature colour; a locked roster entry drops to Text Faint until it opens.

**The Red Means Danger Rule.** Red is reserved for danger, sudden death, losses and errors. It is never decorative.

## Typography

**Display Font:** Silkscreen (with monospace)
**Body Font:** Archivo Variable (with Archivo, system-ui, sans-serif)

**Character:** Silkscreen is a blocky, caps-only bitmap face that speaks for the game; Archivo is a plain grotesque that does the explaining. Pixelify Sans was tried and rejected: its C reads as O and its 5 as S, which breaks names and scores.

### Hierarchy
- **Display** (Silkscreen 700, clamp(2rem, 5.6vw, 4.2rem), 1.1): page titles. Game-moment words run larger: the countdown (clamp(5rem, 12vw, 9rem)) and YOU WIN / YOU LOSE (clamp(2.2rem, 4vw, 3.2rem)).
- **Headline** (Silkscreen 700, clamp(1.3rem, 2.2vw, 1.75rem), 1.1): section titles, panel captions (1.15-1.3rem).
- **Title** (Silkscreen 700, 1-1.2rem, 1.1): fighter names, buttons, the wordmark (1.2rem), stakes values (1.4rem), the HUD timer (1.7rem).
- **Body** (Archivo 400, 1rem, 1.5; long-form 1.06rem at 1.6, max 68ch): all reading text, descriptions, notes, table cells, legends.
- **Label** (Silkscreen 400, 0.72-0.82rem, 0.06em, uppercase): HUD status, roster status, VS card meta strip, nav (0.9rem).
- **Table head** (Archivo 650, 0.8rem, 0.06em, uppercase): column headings in standings and crosstable.

### Named Rules
**The Game Words Rule.** Silkscreen sets only what the game itself would print: names, ratings, timers, scores, buttons, nav and titles. Sentences go in Archivo.

**The Legible Pixels Rule.** A pixel face must keep C, O, 5 and S distinct. Silkscreen passes; Pixelify Sans does not.

**The Tabular Rule.** Numbers are tabular everywhere (set on body).

## Layout

Play is a two-column hall (max 1344px, centred, gutter clamp(16px, 3.4vw, 48px)): left column 1.5fr holds the match HUD, the arena and the roster beneath it; right column (min 320px) holds the VS card and Where you stand. Below 1000px it collapses to one column ordered arena, VS card, roster, and the standings panel hides. The roster is a five-up grid of cards that becomes a single-column list of horizontal rows below 760px. The top bar is 64px, wordmark left, nav right, stacking under 640px. How they learned is a single 1100px column of panels with prose held to 68ch. Spacing runs on a loose 4px rhythm (6, 10, 12, 14, 18, 22, 32px); panels pad 16-22px.

## Elevation & Depth

Depth is a game-menu bevel, not a shadow. Surfaces are flat fills with a 3px Frame Black border and two inset lines: a light top edge and a dark bottom edge. Buttons have a deeper bevel and press down 2px on click, losing the top highlight. Roster cards lift 2px on hover. No ambient or drop shadows on boxes.

### Shadow Vocabulary
- **Panel bevel** (`box-shadow: inset 0 2px 0 rgb(255 255 255 / 0.09), inset 0 -3px 0 rgb(0 0 0 / 0.35)`): panels, quiet buttons, roster cards.
- **Button bevel** (`box-shadow: inset 0 3px 0 rgb(255 255 255 / 0.35), inset 0 -4px 0 rgb(0 0 0 / 0.22)`): the yellow primary button.
- **Button pressed** (`box-shadow: inset 0 -1px 0 rgb(0 0 0 / 0.22)` with `translateY(2px)`): active state.

### Named Rules
**The Bevel Not Blur Rule.** Depth comes from inset bevel lines and the dark frame. Never a soft drop shadow.

## Shapes

Nearly square corners: 4px on panels, buttons, inputs, roster cards and the arena frame; 3px on keycaps and the sudden-death banner. Every container is framed in a 3px Frame Black border; keycaps use a 2px border with a 4px bottom edge. Raster art (tiles, characters, bomb chips) is always rendered with image-rendering: pixelated and image smoothing off, scaled in whole-sprite steps from 16px character grids and 32px tiles.

## Components

### Buttons
Chunky, pressable arcade buttons.
- **Shape:** gently squared (4px), 3px Frame Black border.
- **Primary:** Your Jacket Yellow fill, HUD Deep text, Silkscreen 700 at 1rem, padding 0.75em 1.3em, button bevel. Start match runs full width at 1.2rem.
- **Hover / Focus:** brightness(1.08) over 140ms ease-out; 3px yellow focus outline offset 3px. Active presses down 2px.
- **Quiet:** Raised Panel fill with the panel bevel, for secondary actions.
- **Disabled:** Line fill, Text Dim, no motion.

### Cards / Containers (panel)
- **Corner Style:** 4px.
- **Background:** Menu Panel.
- **Shadow Strategy:** panel bevel (see Elevation).
- **Border:** 3px Frame Black.
- **Internal Padding:** 16-22px.

### Inputs / Fields
- **Style:** HUD Deep fill, 3px Frame Black border, 4px radius, Archivo 1.05rem.
- **Focus:** the global yellow focus ring.
- **Error:** border turns HUD Alarm Red; help text turns red.

### Navigation
Top bar on HUD Deep with a 3px Frame Black bottom border. Yellow Silkscreen wordmark left; Silkscreen nav links at 0.9rem in Text Dim, Text on hover, and Text with a 3px yellow underline for the current page.

### Match HUD (signature)
A HUD Deep strip above the arena: your portrait, name and bomb chip left; the sudden-death countdown centre; the opponent mirrored right. Status lines read BOMB READY in Text Dim and turn Lit Fuse Orange when lit. At sudden death the timer becomes a red banner with HUD Deep lettering that drops in and blinks three times.

### Arena (signature)
A canvas at 32px per tile scaled to its column with crisp pixels, framed 3px and backed by Arena Floor. Floor cells checker floor-light and floor-dark; the original wall, brick (one blast) and stone (two blasts) tiles; the original two-frame bomb that swells near detonation; the original explosion; characters ease between tiles at the tick rate and face their direction of travel. Live matches use the arena_1 map. A tile legend sits under the arena in Archivo.

### VS Card (signature)
A panel with a meta strip (round, map, rated) in uppercase Silkscreen labels over a Frame Black rule; both portraits facing each other with names in their signature colours and ratings; red VS between them; a HUD Deep stakes strip of win / draw / loss deltas (gains yellow, losses red); the yellow Start match button; keycaps for the controls.

### Character-Select Roster (signature)
Five cards from lowest-rated agent to Two-Fuse hard. Each shows the agent's 64px sprite, its name in signature colour, its Elo and a status (NEXT in yellow). The current pick takes a yellow border on a warm olive fill (#3a3a2c). Locked opponents show their own sprite dimmed (grayscale 0.75, brightness 0.7, opacity 0.6) with names and copy in Text Faint.

### Charts
Line charts and dumbbells sit in panels on hairline grids. Series share one hue (Two-Fuse Bone) and are told apart by dash pattern (solid, 7 5, 2 4) plus direct end labels; legend swatches repeat the dash.

## Do's and Don'ts

### Do:
- **Do** use HUD Navy (#1e1e28) for the page and the grey checker floor with the repo's own tile sprites for the arena, drawn pixel-crisp.
- **Do** draw characters from the original 16x16 grids in web/src/art/characters.json.
- **Do** keep Your Jacket Yellow for the player and the player's actions; keep HUD Alarm Red for danger and sudden death.
- **Do** colour every agent's name with its character's signature colour.
- **Do** frame panels in 3px Frame Black (#0c0c12) with the inset bevel.
- **Do** tell chart series apart by dash pattern plus direct labels in a single hue.
- **Do** show locked roster opponents as their own sprite, dimmed.
- **Do** run live matches on arena_1.

### Don't:
- **Don't** use the Bomberman franchise characters, the balloon enemies or the official title art that exist in src/graphics (player.png, enemy.png, enemy_later.png, bomberman_title.png).
- **Don't** return to the tournament-table world: no felt, chalk or score-sheet look.
- **Don't** use Pixelify Sans or any pixel face whose C reads as O or 5 as S.
- **Don't** set sentences or long reading text in Silkscreen.
- **Don't** render locked opponents as silhouettes.
- **Don't** separate chart series by hue alone.
- **Don't** smooth or blur raster art; never resample sprites with smoothing on.
