import type { ReactElement } from "react";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { JSDOM } from "jsdom";

type GlobalKey =
  | "window"
  | "document"
  | "navigator"
  | "HTMLElement"
  | "SVGElement"
  | "Element"
  | "Node"
  | "Event"
  | "MouseEvent"
  | "KeyboardEvent"
  | "PointerEvent"
  | "Image"
  | "DOMPoint"
  | "getComputedStyle"
  | "IS_REACT_ACT_ENVIRONMENT";

const GLOBAL_KEYS: readonly GlobalKey[] = [
  "window",
  "document",
  "navigator",
  "HTMLElement",
  "SVGElement",
  "Element",
  "Node",
  "Event",
  "MouseEvent",
  "KeyboardEvent",
  "PointerEvent",
  "Image",
  "DOMPoint",
  "getComputedStyle",
  "IS_REACT_ACT_ENVIRONMENT",
];

export interface ReactHarness {
  readonly document: Document;
  readonly container: HTMLElement;
  text(selector: string): string;
  disabled(selector: string): boolean;
  click(selector: string): Promise<void>;
  input(selector: string, value: string): Promise<void>;
  change(selector: string, value: string): Promise<void>;
  keyDown(selector: string, key: string, options?: KeyboardEventInit): Promise<void>;
  pointer(selector: string, type: string, options?: PointerEventInit): Promise<void>;
  flush(callback?: () => void | Promise<void>): Promise<void>;
  documentValue(selector: string): string;
  cleanup(): Promise<void>;
}

function requiredElement<T extends Element>(documentValue: Document, selector: string): T {
  const element = documentValue.querySelector<T>(selector);
  if (!element) throw new Error(`Missing test element: ${selector}`);
  return element;
}

function setNativeValue(
  windowValue: {
    HTMLInputElement: { prototype: HTMLInputElement };
    HTMLSelectElement: { prototype: HTMLSelectElement };
  },
  element: HTMLInputElement | HTMLSelectElement,
  value: string,
): void {
  const prototype = element.tagName === "INPUT"
    ? windowValue.HTMLInputElement.prototype
    : windowValue.HTMLSelectElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
  if (!setter) throw new Error("DOM value setter is unavailable");
  setter.call(element, value);
}

export async function renderReact(element: ReactElement): Promise<ReactHarness> {
  const dom = new JSDOM("<!doctype html><html><body><div id=\"root\"></div></body></html>", {
    url: "http://localhost/",
  });
  const descriptors = new Map<GlobalKey, PropertyDescriptor | undefined>();
  const windowValue = dom.window;
  const replacements: Record<GlobalKey, unknown> = {
    window: windowValue,
    document: windowValue.document,
    navigator: windowValue.navigator,
    HTMLElement: windowValue.HTMLElement,
    SVGElement: windowValue.SVGElement,
    Element: windowValue.Element,
    Node: windowValue.Node,
    Event: windowValue.Event,
    MouseEvent: windowValue.MouseEvent,
    KeyboardEvent: windowValue.KeyboardEvent,
    PointerEvent: windowValue.PointerEvent ?? windowValue.MouseEvent,
    Image: windowValue.Image,
    DOMPoint: windowValue.DOMPoint,
    getComputedStyle: windowValue.getComputedStyle.bind(windowValue),
    IS_REACT_ACT_ENVIRONMENT: true,
  };
  for (const key of GLOBAL_KEYS) {
    descriptors.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, {
      configurable: true,
      writable: true,
      value: replacements[key],
    });
  }

  const container = requiredElement<HTMLElement>(windowValue.document, "#root");
  const root: Root = createRoot(container);
  await act(async () => {
    root.render(element);
  });

  let cleaned = false;
  const harness: ReactHarness = {
    document: windowValue.document,
    container,
    text(selector) {
      return requiredElement(windowValue.document, selector).textContent ?? "";
    },
    disabled(selector) {
      return requiredElement<HTMLButtonElement | HTMLInputElement | HTMLSelectElement>(
        windowValue.document,
        selector,
      ).disabled;
    },
    async click(selector) {
      await harness.flush(() => {
        requiredElement<HTMLElement>(windowValue.document, selector).click();
      });
    },
    async input(selector, value) {
      await harness.flush(() => {
        const inputElement = requiredElement<HTMLInputElement>(windowValue.document, selector);
        setNativeValue(windowValue, inputElement, value);
        inputElement.dispatchEvent(new windowValue.Event("input", { bubbles: true }));
      });
    },
    async change(selector, value) {
      await harness.flush(() => {
        const inputElement = requiredElement<HTMLInputElement | HTMLSelectElement>(
          windowValue.document,
          selector,
        );
        setNativeValue(windowValue, inputElement, value);
        inputElement.dispatchEvent(new windowValue.Event("change", { bubbles: true }));
      });
    },
    async keyDown(selector, key, options = {}) {
      await harness.flush(() => {
        requiredElement<Element>(windowValue.document, selector).dispatchEvent(
          new windowValue.KeyboardEvent("keydown", { bubbles: true, key, ...options }),
        );
      });
    },
    async pointer(selector, type, options = {}) {
      await harness.flush(() => {
        const EventConstructor = windowValue.PointerEvent ?? windowValue.MouseEvent;
        requiredElement<Element>(windowValue.document, selector).dispatchEvent(
          new EventConstructor(type, { bubbles: true, ...options }),
        );
      });
    },
    async flush(callback) {
      await act(async () => {
        await callback?.();
        await Promise.resolve();
        await Promise.resolve();
      });
    },
    documentValue(selector) {
      return requiredElement<HTMLInputElement | HTMLSelectElement>(windowValue.document, selector).value;
    },
    async cleanup() {
      if (cleaned) return;
      cleaned = true;
      await act(async () => {
        root.unmount();
      });
      dom.window.close();
      for (const key of [...GLOBAL_KEYS].reverse()) {
        const descriptor = descriptors.get(key);
        if (descriptor) Object.defineProperty(globalThis, key, descriptor);
        else Reflect.deleteProperty(globalThis, key);
      }
    },
  };
  return harness;
}

export const text = (harness: ReactHarness, selector: string): string => harness.text(selector);
export const disabled = (harness: ReactHarness, selector: string): boolean => harness.disabled(selector);
export const click = (harness: ReactHarness, selector: string): Promise<void> => harness.click(selector);
export const input = (harness: ReactHarness, selector: string, value: string): Promise<void> => (
  harness.input(selector, value)
);
export const change = (harness: ReactHarness, selector: string, value: string): Promise<void> => (
  harness.change(selector, value)
);
export const keyDown = (
  harness: ReactHarness,
  selector: string,
  key: string,
  options?: KeyboardEventInit,
): Promise<void> => harness.keyDown(selector, key, options);
export const pointer = (
  harness: ReactHarness,
  selector: string,
  type: string,
  options?: PointerEventInit,
): Promise<void> => harness.pointer(selector, type, options);
export const flush = (
  harness: ReactHarness,
  callback?: () => void | Promise<void>,
): Promise<void> => harness.flush(callback);
export const documentValue = (harness: ReactHarness, selector: string): string => (
  harness.documentValue(selector)
);
export const cleanup = (harness: ReactHarness): Promise<void> => harness.cleanup();
