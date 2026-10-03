"use strict";

// Next's plugin loads this adapter synchronously through CommonJS.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { globSync } = require("tinyglobby");

// This is deliberately not the fast-glob API. Only Next's audited directory
// discovery call is supported. Requalify/remove this override on Next upgrades.
exports.globSync = function nextRootDirectories(pattern, options) {
  if (
    typeof pattern !== "string" ||
    !options ||
    options.onlyDirectories !== true ||
    Object.keys(options).some((key) => key !== "onlyDirectories")
  ) {
    throw new TypeError("Unsupported Next lint directory-glob call");
  }
  return globSync(pattern, {
    onlyDirectories: true,
    expandDirectories: false,
  });
};
