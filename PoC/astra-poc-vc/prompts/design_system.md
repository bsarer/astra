### CRITICAL AIOS UI/UX Design System (MANDATORY):
You MUST strictly follow this design system to ensure all injected widgets look like native components of the AIOS workspace. Do not use random colors or basic HTML forms.
1. **Base Glassmorphic Panels**: The grid container is inherently transparent. If your widget needs a background (like a card, form, or dashboard), use this glassmorphic style: `background: rgba(26, 29, 36, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);`
2. **Typography**: Always use `font-family: 'Inter', system-ui, sans-serif;`.
   - **Primary Text** (Titles, main labels): `color: #f8fafc; font-weight: 500;`
   - **Secondary Text** (Descriptions, meta data): `color: #94a3b8; font-weight: 400;`
3. **Brand Colors (Buttons, Accents, Links)**: 
   - Primary Accent: Use `#3b82f6` (Blue).
   - Glow Effect (for active elements/hover): `box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);`
4. **Interactive Elements (Buttons, Inputs)**:
   - **Buttons**: `background-color: #3b82f6; color: white; border: none; border-radius: 8px; padding: 10px 16px; font-weight: 500; cursor: pointer; transition: all 0.2s;`
   - **Button Hover**: Change background to `#2563eb` and add a slight scale `transform: translateY(-1px);`
   - **Inputs/Textareas**: `background: rgba(15, 17, 21, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; border-radius: 8px; padding: 10px; outline: none; transition: border-color 0.2s;`
   - **Input Focus**: Change border to `#3b82f6`.
5. **Spacing & Layout**: Maintain plenty of breathing space. Use CSS Flexbox or Grid extensively. Use `padding: 20px; gap: 12px;` for inner main containers.
6. **Fluid Sizing**: Your widget HTML MUST fill its container responsively. Wrap your ENTIRE content in a single root `<div style="width: 100%; height: 100%; display: flex; flex-direction: column;">`. All child elements should use percentage-based or flex sizing. NEVER use fixed pixel heights on the root container. The iframe body is already set to `display:flex; align-items:center; justify-content:center;` so your root div will be centered automatically.
7. **Responsive Sizing**: Provide `width_percent` (from 1 to 100, where 100 is full screen) and `height_px` (exact pixels) dynamically based on the widget's intended content size. A generic form or calculator usually needs `width_percent=30, height_px=450`.
