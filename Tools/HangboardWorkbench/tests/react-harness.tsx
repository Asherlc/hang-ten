import type { ReactElement } from "react";
import { act } from "react";
import type { Root } from "react-dom/client";
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
  keyDown(selector: string, key: string, options?: KeyboardEventInit): Promise<boolean>;
  pointer(selector: string, type: string, options?: PointerEventInit): Promise<void>;
  mouse(selector: string, type: string, options?: MouseEventInit): Promise<void>;
  wheel(selector: string, options?: WheelEventInit): Promise<boolean>;
  setSvgGeometry(selector: string, options: {
    rect: Pick<DOMRect, "left" | "top" | "width" | "height">;
    screenCTM?: DOMMatrix | null;
  }): void;
  capturedPointerId(selector: string): number | null;
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
  Object.defineProperties(windowValue.HTMLElement.prototype, {
    attachEvent: {
      configurable: true,
      value() {},
    },
    detachEvent: {
      configurable: true,
      value() {},
    },
  });
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

  let restored = false;
  const restoreBrowserGlobals = (): void => {
    if (restored) return;
    restored = true;
    dom.window.close();
    for (const key of [...GLOBAL_KEYS].reverse()) {
      const descriptor = descriptors.get(key);
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
  };

  const container = requiredElement<HTMLElement>(windowValue.document, "#root");
  const { createRoot } = await import("react-dom/client");
  let root: Root | null = null;
  try {
    root = createRoot(container);
    await act(async () => {
      root?.render(element);
    });
  } catch (error: unknown) {
    try {
      await act(async () => {
        root?.unmount();
      });
    } catch {
      // Preserve the initial rendering failure after releasing test resources.
    } finally {
      restoreBrowserGlobals();
    }
    throw error;
  }

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
        const element = requiredElement<Element>(windowValue.document, selector);
        if (element instanceof windowValue.HTMLElement) element.click();
        else element.dispatchEvent(new windowValue.MouseEvent("click", { bubbles: true, cancelable: true }));
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
      let defaultPrevented = false;
      await harness.flush(() => {
        const element = requiredElement<Element>(windowValue.document, selector);
        const event = new windowValue.KeyboardEvent("keydown", {
          bubbles: true,
          cancelable: true,
          key,
          ...options,
        });
        element.dispatchEvent(event);
        defaultPrevented = event.defaultPrevented;
      });
      return defaultPrevented;
    },
    async pointer(selector, type, options = {}) {
      await harness.flush(() => {
        const EventConstructor = windowValue.PointerEvent ?? windowValue.MouseEvent;
        const event = new EventConstructor(type, {
          bubbles: true,
          cancelable: true,
          ...options,
          ...(Number.isFinite(options.clientX) ? {} : { clientX: 0 }),
          ...(Number.isFinite(options.clientY) ? {} : { clientY: 0 }),
        });
        for (const coordinate of ["clientX", "clientY"] as const) {
          if (options[coordinate] !== undefined && !Number.isFinite(options[coordinate])) {
            Object.defineProperty(event, coordinate, { configurable: true, value: options[coordinate] });
          }
        }
        if (!("pointerId" in event)) {
          Object.defineProperty(event, "pointerId", {
            configurable: true,
            value: options.pointerId ?? 0,
          });
        }
        requiredElement<Element>(windowValue.document, selector).dispatchEvent(event);
      });
    },
    async mouse(selector, type, options = {}) {
      await harness.flush(() => {
        requiredElement<Element>(windowValue.document, selector).dispatchEvent(
          new windowValue.MouseEvent(type, { bubbles: true, cancelable: true, ...options }),
        );
      });
    },
    async wheel(selector, options = {}) {
      let defaultPrevented = false;
      await harness.flush(() => {
        const event = new windowValue.WheelEvent("wheel", {
          bubbles: true,
          cancelable: true,
          ...options,
        });
        requiredElement<Element>(windowValue.document, selector).dispatchEvent(event);
        defaultPrevented = event.defaultPrevented;
      });
      return defaultPrevented;
    },
    setSvgGeometry(selector, { rect, screenCTM }) {
      const svg = requiredElement<SVGSVGElement>(windowValue.document, selector);
      let capturedPointerId: number | null = null;
      Object.defineProperty(svg, "getBoundingClientRect", {
        configurable: true,
        value: () => ({
          ...rect,
          x: rect.left,
          y: rect.top,
          right: rect.left + rect.width,
          bottom: rect.top + rect.height,
          toJSON: () => ({}),
        }),
      });
      Object.defineProperty(svg, "getScreenCTM", {
        configurable: true,
        value: () => screenCTM ?? null,
      });
      Object.defineProperties(svg, {
        setPointerCapture: {
          configurable: true,
          value: (pointerId: number) => { capturedPointerId = pointerId; },
        },
        releasePointerCapture: {
          configurable: true,
          value: (pointerId: number) => {
            if (capturedPointerId === pointerId) capturedPointerId = null;
          },
        },
        __capturedPointerId: {
          configurable: true,
          get: () => capturedPointerId,
        },
      });
    },
    capturedPointerId(selector) {
      const svg = requiredElement<SVGSVGElement>(windowValue.document, selector);
      const instrumented = svg as SVGSVGElement & { __capturedPointerId?: number | null };
      if (!("__capturedPointerId" in instrumented)) {
        throw new Error(`Call setSvgGeometry before reading pointer capture: ${selector}`);
      }
      return instrumented.__capturedPointerId ?? null;
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
      try {
        await act(async () => {
          root?.unmount();
        });
      } finally {
        restoreBrowserGlobals();
      }
    },
  };
  return harness;
}
