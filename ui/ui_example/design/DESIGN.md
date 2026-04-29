---
name: The Academic Editorial - Golden Idea
colors:
  surface: '#f8f9fa'
  surface-dim: '#d8dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3f4'
  surface-container: '#eceeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#424654'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#eff1f2'
  outline: '#747784'
  outline-variant: rgba(25, 28, 29, 0.2)
  surface-tint: '#2c59ba'
  primary: '#002b73'
  on-primary: '#ffffff'
  primary-container: '#0056d2'
  on-primary-container: '#98b3ff'
  inverse-primary: '#b2c5ff'
  secondary: '#435b9f'
  on-secondary: '#ffffff'
  secondary-container: '#9cb4fe'
  on-secondary-container: '#2a4486'
  tertiary: '#5d1900'
  on-tertiary: '#ffffff'
  tertiary-container: '#822803'
  on-tertiary-container: '#ff9c7a'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b2c5ff'
  on-primary-fixed: '#001848'
  on-primary-fixed-variant: '#0040a1'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b3c5ff'
  on-secondary-fixed: '#00184a'
  on-secondary-fixed-variant: '#2a4385'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59d'
  on-tertiary-fixed: '#390c00'
  on-tertiary-fixed-variant: '#822803'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#eeeeee'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 56px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.0'
    letterSpacing: 0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  '1': 0.25rem
  '2': 0.5rem
  '4': 1.5rem
  '8': 2.75rem
  '16': 5.5rem
---

# Design System Specification: The Academic Editorial



## 1. Overview & Creative North Star

The Creative North Star for this design system is **"The Digital Curator."**



In a corporate E-learning environment, users are often overwhelmed by "data-dump" interfaces. This system moves beyond the generic LMS template by adopting a high-end editorial approach. We treat educational content like a premium digital publication—utilizing intentional asymmetry, extreme whitespace, and a sophisticated typographic scale to guide the learner’s eye.



Instead of rigid, boxed-in grids, we use **Tonal Layering** and **Architectural Breathing Room** to define the interface. The result is a system that feels authoritative yet approachable, fostering a state of "focused calm" necessary for deep learning.



---



## 2. Colors: Tonal Architecture

This system relies on a sophisticated palette of professional blues and monochromatic surfaces to establish trust and hierarchy.



### The "No-Line" Rule

**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or layout containment. Boundaries must be defined solely through background color shifts. For example, a `surface-container-low` section should sit directly against a `surface` background. The "edge" is the color change itself, creating a cleaner, more modern finish.



### Surface Hierarchy & Nesting

Treat the UI as a series of physical layers. Use the `surface-container` tiers to create depth through nesting:

- **Surface (Base):** `#f8f9fa` - The canvas.

- **Surface-Container-Lowest:** `#ffffff` - Used for primary content cards or active lesson modules to make them "pop" against the base.

- **Surface-Container-High:** `#e7e8e9` - Used for secondary sidebars or utility panels.



### The "Glass & Gradient" Rule

To avoid a "flat" corporate feel, utilize Glassmorphism for floating elements (like progress trackers or navigation bars).

- **Glass Effect:** Use semi-transparent versions of `surface` with a `24px` backdrop-blur.

- **Signature Textures:** For primary CTAs and Hero backgrounds, use a subtle linear gradient (135°) transitioning from `primary` (#0040a1) to `primary_container` (#0056d2). This adds "soul" and visual depth that flat hex codes cannot achieve.



---



## 3. Typography: Editorial Authority

We pair **Manrope** (Display/Headlines) with **Inter** (Body/UI) to create a "Technical-Editorial" aesthetic. Manrope’s geometric warmth provides personality, while Inter’s neutrality ensures maximum legibility during long-form reading.



* **Display-LG (56px):** Reserved for hero welcome messages and course titles. Use `on_surface` with `-0.02em` letter spacing for a premium "tight" feel.

* **Headline-MD (28px):** Used for module headings. These should often be placed with asymmetrical padding to create visual interest.

* **Body-LG (16px):** The workhorse for course content. Set line-height to `1.6` to prevent learner fatigue.

* **Label-MD (12px):** Used for metadata (e.g., "15 mins left," "Intermediate"). Always use `on_surface_variant` (#424654) to ensure a clear hierarchy against primary text.



---



## 4. Elevation & Depth: Tonal Layering

Traditional shadows and borders are hallmarks of "standard" UI. This system replaces them with environmental light and surface shifts.



* **The Layering Principle:** Rather than lifting an object with a shadow, "elevate" it by placing a `surface-container-lowest` card on a `surface-container-low` background. The contrast in lightness creates a soft, natural lift.

* **Ambient Shadows:** If a floating element (like a Modal) requires a shadow, use a "Cloud Shadow": `0px 20px 40px rgba(25, 28, 29, 0.05)`. The shadow color is a 5% opacity tint of the `on_surface` token, mimicking natural light.

* **The "Ghost Border" Fallback:** If a border is required for accessibility in input fields, use the `outline_variant` token at **20% opacity**. Never use 100% opaque lines.

* **Glassmorphism:** Use semi-transparent `surface` layers for top navigation. This allows the course content to bleed through as the user scrolls, creating a sense of continuity.



---



## 5. Components: Refined Interaction



### Buttons (The Anchor)

* **Primary:** Gradient of `primary` to `primary_container`. Roundedness: `md` (0.75rem). No border.

* **Tertiary:** No background. Use `primary` text. On hover, apply a `surface-container-low` background pill shape.



### Inputs & Search

* **Styling:** Use `surface-container-low` as the background fill. No border. On focus, transition the background to `surface-container-lowest` and apply a 1px `primary` ghost-border (30% opacity).



### Cards & Progress Modules

* **Rule:** Forbid the use of divider lines.

* **Layout:** Separate content using the spacing scale (e.g., `8` (2.75rem) between sections). Use `surface-container-lowest` for the card body and `surface-variant` for a subtle "footer" area within the card.



### Learning Specific Components

* **The "Progress Float":** A glassmorphic sticky bar at the bottom of the viewport using `surface` at 80% opacity and `primary` for the progress indicator.

* **Knowledge Checks:** Use `secondary_container` (#9cb4fe) for "Success" feedback areas and `error_container` (#ffdad6) for "Retry" states, maintaining a soft, non-punitive tone.



---



## 6. Do’s and Don’ts



### Do:

* **Embrace Asymmetry:** Align course titles to the left but place metadata (time, difficulty) in staggered, non-traditional positions.

* **Use Generous Padding:** Use the `16` (5.5rem) spacing token for top/bottom margins of major lesson sections.

* **Prioritize Typography:** Let the size and weight of Manrope do the heavy lifting of organization, not boxes.



### Don’t:

* **Don't use 1px solid dividers:** This is the quickest way to make the design look like a legacy enterprise tool.

* **Don't use pure black:** Use `on_surface` (#191c1d) for text to maintain a softer, higher-end look.

* **Don't use harsh corners:** Always stick to the `md` (0.75rem) or `lg` (1rem) roundedness scale to keep the "friendly" professional tone.