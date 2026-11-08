<script lang="ts">
  /** A character portrait: one pixel-art frame scaled up with crisp pixels. Decorative; names carry the meaning. */
  import { onMount } from "svelte";
  import { characterFrames, type CharacterKey, SPRITE } from "../art/sprites";

  interface Props {
    character: CharacterKey;
    size?: number;
    animate?: boolean;
    dim?: boolean;
  }

  let { character, size = 64, animate = false, dim = false }: Props = $props();
  let canvas: HTMLCanvasElement;
  let frame = $state(0);

  $effect(() => {
    const ctx = canvas?.getContext("2d");
    if (!ctx) return;
    const frames = characterFrames(character);
    ctx.clearRect(0, 0, SPRITE, SPRITE);
    ctx.drawImage(frames[frame % frames.length]!, 0, 0);
  });

  onMount(() => {
    if (!animate) return;
    const timer = setInterval(() => (frame += 1), 420);
    return () => clearInterval(timer);
  });
</script>

<canvas
  bind:this={canvas}
  width={SPRITE}
  height={SPRITE}
  aria-hidden="true"
  class:dim
  style:width={`${size}px`}
  style:height={`${size}px`}
></canvas>

<style>
  canvas {
    display: block;
    image-rendering: pixelated;
    flex: none;
  }
  .dim {
    filter: grayscale(0.75) brightness(0.7);
    opacity: 0.6;
  }
</style>
