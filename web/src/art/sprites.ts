/**
 * The game's art. Tiles (walls, bricks, bomb, explosion) are the generic
 * sprites from src/graphics, copied unchanged. Characters are original 16x16
 * pixel art authored in characters.json and painted onto canvases at load,
 * so they stay crisp at any scale with image smoothing off.
 */
import characters from "./characters.json";

export type CharacterKey = "you" | "spark" | "camper" | "wanderer" | "heuristic" | "two_fuse_normal" | "two_fuse_hard";

interface CharacterSpec {
  name: string;
  palette: Record<string, string>;
  frames: string[][] | string;
}

const SPECS = characters as Record<CharacterKey, CharacterSpec>;
export const SPRITE = 16;

/** The signature colour each character is drawn in, for names and accents. */
export const SIGNATURE: Record<CharacterKey, string> = {
  you: "#f2b51d",
  spark: "#ff7a1a",
  camper: "#5fb36a",
  wanderer: "#3fc9b8",
  heuristic: "#c4ccd4",
  two_fuse_normal: "#ece6d6",
  two_fuse_hard: "#ff6a5a",
};

function framesOf(key: CharacterKey): string[][] {
  const frames = SPECS[key].frames;
  return typeof frames === "string" ? framesOf(frames as CharacterKey) : frames;
}

const cache = new Map<CharacterKey, HTMLCanvasElement[]>();

/** The character's frames as 16x16 canvases (browser only). */
export function characterFrames(key: CharacterKey): HTMLCanvasElement[] {
  const hit = cache.get(key);
  if (hit) return hit;
  const palette = SPECS[key].palette;
  const frames = framesOf(key).map((rows) => {
    const canvas = document.createElement("canvas");
    canvas.width = SPRITE;
    canvas.height = SPRITE;
    const ctx = canvas.getContext("2d")!;
    rows.forEach((row, y) => {
      [...row].forEach((ch, x) => {
        if (ch === ".") return;
        ctx.fillStyle = palette[ch] ?? "#ff00ff";
        ctx.fillRect(x, y, 1, 1);
      });
    });
    return canvas;
  });
  cache.set(key, frames);
  return frames;
}

/** Draw a character into a square box, optionally mirrored to face left. */
export function drawCharacter(
  ctx: CanvasRenderingContext2D,
  key: CharacterKey,
  frame: number,
  x: number,
  y: number,
  size: number,
  faceLeft = false,
): void {
  const frames = characterFrames(key);
  const image = frames[frame % frames.length]!;
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  if (faceLeft) {
    ctx.translate(x + size, y);
    ctx.scale(-1, 1);
    ctx.drawImage(image, 0, 0, size, size);
  } else ctx.drawImage(image, x, y, size, size);
  ctx.restore();
}

export const TILE_FILES = {
  wall: "/sprites/wall.png",
  brick: "/sprites/destrWall.png",
  stone: "/sprites/destrWall_1.png",
  bomb: "/sprites/bomb.png",
  explosion: "/sprites/explosion.png",
} as const;

export type Tiles = Record<keyof typeof TILE_FILES, HTMLImageElement>;

let tiles: Promise<Tiles> | null = null;

/** The tile images, loaded once. */
export function loadTiles(): Promise<Tiles> {
  tiles ??= Promise.all(
    Object.entries(TILE_FILES).map(
      ([name, src]) =>
        new Promise<[string, HTMLImageElement]>((resolve, reject) => {
          const image = new Image();
          image.onload = () => resolve([name, image]);
          image.onerror = reject;
          image.src = src;
        }),
    ),
  ).then((entries) => Object.fromEntries(entries) as Tiles);
  return tiles;
}
