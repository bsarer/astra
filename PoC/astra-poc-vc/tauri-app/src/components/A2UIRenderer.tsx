import React from "react";
import { componentMap, fallbackComponent } from "./componentMap";

interface A2UIComponent {
  id: string;
  type: string;
  props: Record<string, any>;
  children: string[];
}

interface A2UIRendererProps {
  components: A2UIComponent[];
  onAction?: (action: string, payload?: Record<string, any>) => void;
}

/**
 * Renders an A2UI adjacency list into React components using the componentMap.
 * Walks the tree from the first component (root) and recursively renders children.
 */
export function A2UIRenderer({ components, onAction }: A2UIRendererProps) {
  if (!components || components.length === 0) return null;

  const compMap = new Map<string, A2UIComponent>();
  for (const c of components) {
    compMap.set(c.id, c);
  }

  const root = components[0];
  return <>{renderComponent(root, compMap, onAction, new Set())}</>;
}

function renderComponent(
  comp: A2UIComponent,
  compMap: Map<string, A2UIComponent>,
  onAction?: (action: string, payload?: Record<string, any>) => void,
  visited?: Set<string>
): React.ReactNode {
  if (!comp) return null;

  // Cycle detection
  const seen = visited || new Set<string>();
  if (seen.has(comp.id)) return null;
  seen.add(comp.id);

  const Component = componentMap[comp.type];
  const FallbackComp = fallbackComponent;

  // Resolve children
  const children = comp.children || [];
  const childElements = children
    .map((childId) => compMap.get(childId))
    .filter(Boolean)
    .map((child) => renderComponent(child!, compMap, onAction, new Set(seen)));

  const props = { ...comp.props, onAction, key: comp.id };

  if (Component) {
    if (children.length > 0) {
      return <Component {...props}>{childElements}</Component>;
    }
    return <Component {...props} />;
  }

  // Fallback for unknown types
  return (
    <FallbackComp key={comp.id} type={comp.type} props={comp.props}>
      {childElements.length > 0 ? childElements : undefined}
    </FallbackComp>
  );
}
