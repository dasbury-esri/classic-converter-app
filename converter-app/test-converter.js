/**
 * Simple test to verify TypeScript converter produces correct output
 * Run with: node test-converter.js
 */

import fs from "fs";
import { convertClassicToJson } from "./src/converter/converter-factory.ts";

// Test with the classic story that has nested images
const classicFile =
  "../test_data/classics/858c4126f0604d1a86dea06ffbdc23a3.json";
const outputFile =
  "../test_data/app-results/858c4126f0604d1a86dea06ffbdc23a3-test.json";

console.log("Loading classic story...");
const classicJson = JSON.parse(fs.readFileSync(classicFile, "utf-8"));

console.log("Converting...");
const storymapJson = convertClassicToJson(classicJson, "summit");

console.log("Saving output...");
fs.writeFileSync(outputFile, JSON.stringify(storymapJson, null, 2));

console.log(`\nResults:`);
console.log(`  Nodes: ${Object.keys(storymapJson.nodes).length}`);
console.log(`  Resources: ${Object.keys(storymapJson.resources).length}`);

// Check for the specific nested image
const hasBufferedImage = Object.values(storymapJson.resources).some(
  (r) =>
    r.type === "image" &&
    (r.data.resourceId?.includes("Buffered") ||
      r.data.src?.includes("Buffered"))
);

console.log(
  `  Buffered Bike Lanes image: ${hasBufferedImage ? "✅ FOUND" : "❌ MISSING"}`
);
console.log(`\nOutput saved to: ${outputFile}`);
