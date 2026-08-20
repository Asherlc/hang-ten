import { createRoot, type Root } from "react-dom/client";

import { WorkbenchApp } from "./WorkbenchApp.tsx";
import { postNativeDiagnostic } from "./native-bridge.ts";
import * as pathEditorModule from "./path-editor.ts";
import type {
  BrowserRuntime,
  Dialogs,
  PathEditor,
  WorkbenchController,
  WorkbenchDependencies,
} from "./types.ts";
import { createWorkbenchClient } from "./workbench-client.ts";
import * as workbenchControllerModule from "./workbench-controller.ts";

export function mountWorkbench(rootElement: HTMLElement, dependencies: WorkbenchDependencies): Root {
  const root = createRoot(rootElement);
  root.render(<WorkbenchApp dependencies={dependencies} />);
  return root;
}

const browser = globalThis;
const dialogs: Dialogs = {
  confirm: (message) => browser.confirm(message),
  prompt: (message, defaultValue) => browser.prompt(message, defaultValue),
};
const imageLoader = (): HTMLImageElement => new browser.Image();
const runtime: BrowserRuntime = {
  fetch: (input, init) => browser.fetch(input, init),
  location: {
    assign: (url) => browser.location.assign(url),
  },
  postDiagnostic: (diagnostic) => {
    postNativeDiagnostic(browser, diagnostic);
  },
  createImage: imageLoader,
  ...dialogs,
};
const client = createWorkbenchClient(runtime);
const controller: WorkbenchController = workbenchControllerModule;
const pathEditor: PathEditor = pathEditorModule;
if (typeof browser.document !== "undefined") {
  const rootElement = browser.document.getElementById("root");
  if (rootElement === null) throw new Error("Workbench root element is missing");
  mountWorkbench(rootElement, {
    client,
    controller,
    pathEditor,
    runtime,
    dialogs,
  });
}
