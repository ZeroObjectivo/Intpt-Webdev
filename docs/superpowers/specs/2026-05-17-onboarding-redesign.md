# Onboarding Flow Redesign - Component Architecture

## Overview
Rebuild the 8-screen Herons' Hub onboarding prototype with proper viewport-relative sizing and reusable JS component functions. Standalone Tailwind + HTML + vanilla JS (no React).

## Reference
- Figma canvas: 1920x1080
- All positioning/sizing derived from Figma pixel values converted to vw/vh
- Metropolis font, GSAP animations

## Components

### 1. HeronLogo
SVG heron bird with slate-400 to blue-900 linear gradient.

| Size | Dimensions | Usage |
|------|-----------|-------|
| `lg` | 9.4vw (180px@1920) | Splash screen (S1) |
| `md` | 6.67vw (128px@1920) | Brand lockups (S2-S8 headers) |

### 2. BrandHeader
Horizontal lockup: HeronLogo(md) + text block.

- "HERONS' HUB": `clamp(1.5rem, 2.5vw, 3rem)`, font-medium, text-slate-600
- "Community for everyone": `clamp(0.75rem, 1.04vw, 1.25rem)`, font-thin, text-black
- Positioned: absolute, top ~10.7vh (116/1080), left 50% translateX(-5%)

### 3. OnboardingCard
Two variants sharing the same shape.

| Variant | Background | Radius | Shadow |
|---------|-----------|--------|--------|
| `solid` | `#64748b` (slate-500) | `clamp(24px, 2.6vw, 50px)` | `6px 9px 27px 6px rgba(0,0,0,0.30)` |
| `glass` | `rgba(59,130,246,0.20)` | same | same |

Content card (large) variant: radius `clamp(28px, 2.9vw, 55px)`, shadow `6.7px 10px 30px 6.7px rgba(0,0,0,0.30)`.

### 4. FanStack
Group of 4 OnboardingCards in a fanned arrangement.

**Center layout** (welcome screen S4):
- Card 1 (Solid): rotate(-30deg), margin-left -20.8vw
- Card 2 (Glass): rotate(-15deg), margin-left -10.4vw
- Card 3 (Solid): rotate(15deg), margin-left 2.6vw
- Card 4 (Glass): rotate(30deg), margin-left 13vw
- Each card: ~24.8vw wide, positioned absolute bottom, rising from off-screen

**Left layout** (content screens S5-S7):
- Card 1 (Solid): rotate(5.19deg), bottom-left
- Card 2 (Glass): rotate(20.19deg), overlapping
- Card 3 (Solid, optional): rotate(50.19deg)

### 5. DotNav
Three dots in violet color scheme.

- Active dot: `#7c3aed` (violet-600)
- Inactive dot: `#3b0764` (violet-950)
- Size: `clamp(1.5rem, 2.08vw, 2.5rem)`
- Spacing: letter-spacing 24.8px (scaled: `clamp(12px, 1.29vw, 24.8px)`)
- Position: absolute, bottom ~5.5vh, left ~60%

### 6. ContentSlide
Reusable split layout for screens S5, S6, S7.

- Left side (text): absolute, left 10%, top 32%
  - Title: `clamp(2rem, 3.125vw, 3.75rem)`, font-normal, text-black
  - Body: `clamp(1.25rem, 2.08vw, 2.5rem)`, font-normal, text-black/60
- Right side (card): absolute, right 3%, top ~27%, width 48.9vw, height 54.4vh
- Includes: BrandHeader, FanStack(left), DotNav

## Screens

| # | Content | Unique Elements |
|---|---------|-----------------|
| S1 | Splash | HeronLogo(lg) centered |
| S2 | Brand reveal | HeronLogo(md) + text slide-in |
| S3 | Button peek | S2 + solid card-shaped button rising from bottom |
| S4 | Welcome | BrandHeader + heading + FanStack(center) + "click anywhere" |
| S5 | Slide 1 | ContentSlide(glass) + FanStack(left, 3 cards) |
| S6 | Slide 2 | ContentSlide(solid) + FanStack(left, 2 cards) |
| S7 | Slide 3 | ContentSlide(glass) + FanStack(left, 2 cards) + CTA button |

## Animation Spec (GSAP)

- Screen transitions: crossfade 0.4s power3.out
- Logo entrance: elastic.out(1, 0.5) 1.2s
- Text reveals: power3.out 0.8s, x offset 50px
- Fan cards: staggered 0.12s each, back.out(1) 1.2s, rising from y +300
- Content slides: left from x:-50, right from x:+60, 0.8s power3.out
- Dot nav: fade 0.5s with 0.4s delay

## File Structure
Single `index.html` with:
1. Tailwind CDN + config
2. Metropolis font + GSAP CDN
3. `<style>` block: base styles + component CSS classes
4. `<script>` block: component factory functions + screen builders + animation engine
