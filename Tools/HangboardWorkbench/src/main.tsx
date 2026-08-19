import { createRoot, type Root } from "react-dom/client";

import { WorkbenchApp } from "./WorkbenchApp.tsx";
import type { WorkbenchDependencies } from "./types.ts";

export function mountWorkbench(rootElement: HTMLElement, dependencies: WorkbenchDependencies): Root {
  const root = createRoot(rootElement);
  root.render(<WorkbenchApp dependencies={dependencies} />);
  return root;
}
