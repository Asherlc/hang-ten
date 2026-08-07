(function exposeVectorPathModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HoldVectorPathModel = api;
}(typeof globalThis === "object" ? globalThis : this, () => {
  "use strict";

  const PARAMETER_COUNT = { M: 2, L: 2, Q: 4, C: 6, Z: 0 };

  function parseDisplayPath(data) {
    if (typeof data !== "string") throw new TypeError("Display path must be a string");
    const tokens = tokenize(data);
    const commands = [];
    let index = 0;
    while (index < tokens.length) {
      const type = tokens[index];
      if (typeof type !== "string") throw new TypeError("Expected a display path command");
      index += 1;
      const count = PARAMETER_COUNT[type];
      const values = tokens.slice(index, index + count);
      if (values.length !== count || values.some((value) => typeof value !== "number")) {
        throw new TypeError(`Expected ${String(count)} numeric values for ${type}`);
      }
      index += count;
      commands.push(commandFromValues(type, values));
    }
    return validatePathStructure(commands);
  }

  function serializeDisplayPath(commands) {
    return validateCommands(commands).map((command) => {
      const values = valuesForCommand(command);
      return values.length === 0 ? command.type : `${command.type} ${values.map(formatNumber).join(" ")}`;
    }).join(" ");
  }

  function transformPath(commands, matrix) {
    const [a, b, c, d, e, f] = normalizeMatrix(matrix);
    return validateCommands(commands).map((command) => transformCommand(command, (x, y) => [
      a * x + c * y + e,
      b * x + d * y + f,
    ]));
  }

  function bendPath(commands, amount, bounds) {
    assertFinite(amount, "Bend amount");
    const { minX, width } = normalizeBounds(bounds);
    return validateCommands(commands).map((command) => transformCommand(command, (x, y) => {
      const progress = Math.max(0, Math.min(1, (x - minX) / width));
      return [x, y + amount * 4 * progress * (1 - progress)];
    }));
  }

  function mirrorPath(commands, axisX) {
    assertFinite(axisX, "Mirror axis");
    return transformPath(commands, [-1, 0, 0, 1, axisX * 2, 0]);
  }

  function tokenize(data) {
    const tokens = [];
    let index = 0;
    while (index < data.length) {
      const character = data[index];
      if (/\s|,/.test(character)) {
        index += 1;
        continue;
      }
      const match = data.slice(index).match(/^[+-]?(?:(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?|Infinity|NaN)/);
      if (match) {
        const value = Number(match[0]);
        assertFinite(value, "Display path coordinate");
        tokens.push(value);
        index += match[0].length;
        continue;
      }
      if (/[A-Za-z]/.test(character)) {
        if (!Object.hasOwn(PARAMETER_COUNT, character)) throw new TypeError(`Unsupported display path command: ${character}`);
        tokens.push(character);
        index += 1;
        continue;
      }
      throw new TypeError(`Invalid display path token at position ${String(index)}`);
    }
    return tokens;
  }

  function commandFromValues(type, values) {
    switch (type) {
      case "M": return { type, x: values[0], y: values[1] };
      case "L": return { type, x: values[0], y: values[1] };
      case "Q": return { type, x1: values[0], y1: values[1], x: values[2], y: values[3] };
      case "C": return { type, x1: values[0], y1: values[1], x2: values[2], y2: values[3], x: values[4], y: values[5] };
      case "Z": return { type };
      default: throw new TypeError(`Unsupported display path command: ${type}`);
    }
  }

  function transformCommand(command, transform) {
    if (command.type === "Z") return { type: "Z" };
    const transformPoint = (x, y) => {
      const point = transform(x, y);
      assertFinite(point[0], "Transformed display path coordinate");
      assertFinite(point[1], "Transformed display path coordinate");
      return point;
    };
    const endpoint = transformPoint(command.x, command.y);
    if (command.type === "M" || command.type === "L") return { type: command.type, x: endpoint[0], y: endpoint[1] };
    const firstHandle = transformPoint(command.x1, command.y1);
    if (command.type === "Q") return {
      type: "Q", x1: firstHandle[0], y1: firstHandle[1], x: endpoint[0], y: endpoint[1],
    };
    const secondHandle = transformPoint(command.x2, command.y2);
    return {
      type: "C", x1: firstHandle[0], y1: firstHandle[1], x2: secondHandle[0], y2: secondHandle[1], x: endpoint[0], y: endpoint[1],
    };
  }

  function validateCommands(commands) {
    if (!Array.isArray(commands)) throw new TypeError("Display path commands must be an array");
    const validated = commands.map((command) => {
      if (!command || typeof command !== "object") throw new TypeError("Display path command must be an object");
      const count = PARAMETER_COUNT[command.type];
      if (count === undefined) throw new TypeError(`Unsupported display path command: ${String(command.type)}`);
      for (const value of valuesForCommand(command)) assertFinite(value, "Display path coordinate");
      return command;
    });
    return validatePathStructure(validated);
  }

  function validatePathStructure(commands) {
    if (commands.length === 0) throw new TypeError("Display path cannot be empty");
    let subpathOpen = false;
    for (const command of commands) {
      if (command.type === "M") {
        if (subpathOpen) throw new TypeError("Each display path subpath must be closed before starting another");
        subpathOpen = true;
      } else if (!subpathOpen) {
        throw new TypeError("Each display path subpath must start with M");
      } else if (command.type === "Z") {
        subpathOpen = false;
      }
    }
    if (subpathOpen) throw new TypeError("Each display path subpath must be closed with Z");
    return commands;
  }

  function valuesForCommand(command) {
    switch (command.type) {
      case "M":
      case "L": return [command.x, command.y];
      case "Q": return [command.x1, command.y1, command.x, command.y];
      case "C": return [command.x1, command.y1, command.x2, command.y2, command.x, command.y];
      case "Z": return [];
      default: throw new TypeError(`Unsupported display path command: ${String(command.type)}`);
    }
  }

  function normalizeMatrix(matrix) {
    const values = Array.isArray(matrix)
      ? matrix
      : matrix && typeof matrix === "object"
        ? [matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f]
        : null;
    if (!values || values.length !== 6) throw new TypeError("Transform matrix must contain six values");
    for (let index = 0; index < 6; index += 1) assertFinite(values[index], "Transform matrix value");
    return values.slice();
  }

  function normalizeBounds(bounds) {
    let minX;
    let maxX;
    if (Array.isArray(bounds) && bounds.length === 4) {
      for (let index = 0; index < 4; index += 1) assertFinite(bounds[index], "Bend bounds value");
      [minX, , maxX] = bounds;
    }
    else if (bounds && typeof bounds === "object" && "width" in bounds) {
      for (const key of ["x", "y", "width", "height"]) assertFinite(bounds[key], `Bend bounds ${key}`);
      minX = bounds.x;
      maxX = bounds.x + bounds.width;
    } else if (bounds && typeof bounds === "object") {
      for (const key of ["minX", "maxX", "minY", "maxY", "left", "right", "top", "bottom"]) {
        if (key in bounds) assertFinite(bounds[key], `Bend bounds ${key}`);
      }
      minX = bounds.minX ?? bounds.left;
      maxX = bounds.maxX ?? bounds.right;
    }
    assertFinite(minX, "Bend bounds minimum x");
    assertFinite(maxX, "Bend bounds maximum x");
    const width = maxX - minX;
    assertFinite(width, "Bend bounds width");
    if (width <= 0) throw new RangeError("Bend bounds must have positive width");
    return { minX, width };
  }

  function assertFinite(value, label) {
    if (!Number.isFinite(value)) throw new TypeError(`${label} must be finite`);
  }

  function formatNumber(value) {
    return Object.is(value, -0) ? "0" : String(value);
  }

  return {
    parseDisplayPath,
    serializeDisplayPath,
    transformPath,
    bendPath,
    mirrorPath,
  };
}));
