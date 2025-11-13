/**
 * Classic StoryMap to ArcGIS StoryMaps Converter UI
 * Minimal form interface for conversion
 */

import { useState } from "react";
import { useAuth } from "../auth/AuthProvider";
import {
  getItemData,
  getItemDetails,
  getUsername,
  findDraftResourceName,
  removeResource,
  addResource,
  updateItemKeywords,
} from "../api/arcgis-client";
import { convertClassicToJson } from "../converter/converter-factory";
import { createDraftStoryMap } from "../converter/storymap-draft-creator"
import {
  collectImageUrls,
  transferImages,
  updateImageUrlsInJson,
} from "../api/image-transfer";
// import { saveJsonToFile } from '../converter/utils';

type Status =
  | "idle"
  | "fetching"
  | "converting"
  | "transferring"
  | "updating"
  | "success"
  | "error";

export default function Converter() {
  const { token } = useAuth();
  const [classicItemId, setClassicItemId] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [convertedUrl, setConvertedUrl] = useState("");
  const [publishing, setPublishing] = useState(false);

  const handleConvert = async () => {
    // Reset state
    setStatus("idle");
    setMessage("");
    setConvertedUrl("");

    // Validate token
    if (!token) {
      setStatus("error");
      setMessage("You must be signed in to ArcGIS Online or ArcGIS Enterprise");
      return;
    }

    // // Validate inputs
    // if (!classicItemId.trim()) {
    //   setStatus("error");
    //   setMessage("Please enter a Classic Story Item ID");
    //   return;
    // }

    try {
      // 1. Get username
      setStatus("fetching");
      setMessage("Getting user information...");
      const username = await getUsername(token);

      // 2. Fetch classic item data
      setMessage("Fetching classic story data...");
      const classicData = await getItemData(classicItemId, token);

      // 2.5 Fetch classic webmap data
      if (classicData.values.webmap) {
        setMessage("Fetching classic webmap data...");
        const webmapId = classicData.values.webmap;
        classicData.webmapJson = await getItemData(webmapId, token);
      }

      // 3. Create an empty draft StoryMap
      setMessage("Creating new StoryMap draft...");
      const coverTitle = classicData.values?.title || "Untitled Story";
      const itemTitle = `(Converted) ${coverTitle}`;
      const targetStoryId = await createDraftStoryMap(token, username, itemTitle);

      if (targetStoryId) {
        console.log("Target Story ID is set!")
        console.log("targetStoryId:", targetStoryId);
      }

      // 3.5 Convert to new JSON
      setStatus("converting");
      setMessage("Converting classic story to new format...");
      let newStorymapJson = await convertClassicToJson(
        classicData, 
        "summit", 
        username,
        token,
        targetStoryId);

      console.log("***JSON***",newStorymapJson)
      // 4. Transfer images from classic to target story
      const imageUrls = collectImageUrls(newStorymapJson);
      console.log('Collected image URLs:', imageUrls);
      if (imageUrls.length > 0) {
        setStatus("transferring");
        setMessage(
          `Transferring ${imageUrls.length} image(s) from classic story...`
        );

        const transferResultsArray = await transferImages(
          imageUrls,
          targetStoryId,
          username,
          token,
          (current, total, msg) => {
            setMessage(`Transferring images (${current}/${total}): ${msg}`);
          }
        );
        console.log('[Converter.tsx] Transfer results array:', transferResultsArray);

        // Convert array to mapping
        const transferResults: Record<string, string> = {};
        for (const result of transferResultsArray) {
          transferResults[result.originalUrl] = result.resourceName;
        }

        // Update JSON to use proper resource structure
        // (resourceId + provider for uploaded, src + provider for external)
        newStorymapJson = updateImageUrlsInJson(
          newStorymapJson,
          transferResults
        );
      }

      // 5. Fetch target draft details
      setStatus("updating");
      setMessage("Fetching target storymap details...");
      const targetDetails = await getItemDetails(targetStoryId, token);

      // 6. Find draft resource name
      const draftResourceName = findDraftResourceName(targetDetails);
      if (!draftResourceName) {
        throw new Error(
          "Could not find draft resource in target storymap. Make sure it is a draft storymap."
        );
      }

      // 7. Remove old draft resource
      setMessage(`Removing old draft resource (${draftResourceName})...`);
      await removeResource(targetStoryId, username, draftResourceName, token);

      // 8. Upload new draft resource (same name)
      setMessage(`Uploading new draft resource (${draftResourceName})...`);
      const jsonBlob = new Blob([JSON.stringify(newStorymapJson)], {
        type: "application/json",
      });
      await addResource(
        targetStoryId,
        username,
        jsonBlob,
        draftResourceName,
        token
      );

      // 9. Update keywords to add smconverter:online-app
      setMessage("Updating keywords...");
      const currentKeywords = targetDetails.typeKeywords || [];
      if (!currentKeywords.includes("smconverter:online-app")) {
        const newKeywords = [...currentKeywords, "smconverter:online-app"];
        await updateItemKeywords(targetStoryId, username, newKeywords, token);
      }

      // 3.1 Save JSON for debugging
      // saveJsonToFile(classicData, 'classic_json.json');
      // saveJsonToFile(classicData.webmapJson, 'webmap_json.json');
      // saveJsonToFile(newStorymapJson, 'converted_storymap_json.json');

      // Success!
      setStatus("success");
      setMessage("Conversion complete!");
      setConvertedUrl(
        `https://storymaps.arcgis.com/stories/${targetStoryId}/edit`
      );
      setPublishing(true);
    } catch (error: any) {
      setStatus("error");
      setMessage(`Error: ${error.message || "An unknown error occurred"}`);
      console.error("Conversion error:", error);
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "20px" }}>
      <h1>Classic StoryMap Converter</h1>
      <p>
        Convert Classic StoryMaps (Map Tour, Map Journal, Map Series, Cascade) to ArcGIS
        StoryMaps
      </p>

      <div style={{ marginBottom: "20px" }}>
        <label
          style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}
        >
          Classic Story Item ID:
        </label>
        <input
          type="text"
          value={classicItemId}
          onChange={(e) => setClassicItemId(e.target.value)}
          placeholder="e.g., 858c4126f0604d1a86dea06ffbdc23a3"
          style={{
            width: "100%",
            padding: "10px",
            fontSize: "14px",
            border: "1px solid #ccc",
            borderRadius: "4px",
            boxSizing: "border-box" 
          }}
        />
      </div>

      <button
        onClick={handleConvert}
        disabled={
          publishing || (status !== "idle" && status !== "error" && status !== "success")
        }
        style={{
          width: "100%",
          padding: "12px",
          fontSize: "16px",
          fontWeight: "bold",
          color: "white",
          backgroundColor:
            publishing || (status !== "idle" && status !== "error" && status !== "success")
              ? "#ccc"
              : "#0079c1",
          border: "none",
          borderRadius: "4px",
          cursor:
            publishing || (status !== "idle" && status !== "error" && status !== "success")
              ? "not-allowed"
              : "pointer",
        }}
      >
        {status === "idle" || status === "error" || status === "success"
          ? "Convert"
          : "Converting..."}
      </button>

      {message && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            borderRadius: "4px",
            backgroundColor:
              status === "error"
                ? "#ffe6e6"
                : status === "success"
                ? "#2B5B2B" //"#e6ffe6"
                : "#e6f3ff",
            border: `1px solid ${
              status === "error"
                ? "#ff0000"
                : status === "success"
                ? "#2B5B2B"
                : "#0079c1"
            }`,
            color:
              status === "error"
                ? "#cc0000"
                : status === "success"
                ? "#e3ffe3ff"
                : "#003d5c",
          }}
        >
          <strong>
            {status === "error"
              ? "Error:"
              : status === "success"
              ? "Success:"
              : "Status:"}
          </strong>{" "}
          {message}
        </div>
      )}

      {convertedUrl && (
        <div style={{ marginTop: "20px" }}>
          <button
            style={{
              width: "100%",
              padding: "12px",
              fontSize: "16px",
              fontWeight: "bold",
              color: "white",
              backgroundColor: "#28a745",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer"
            }}
            onClick={() => {
              window.open(convertedUrl, '_blank');
              setPublishing(false);
              setConvertedUrl("");
            }}
            disabled={!publishing}
          >
            Click to Finish Publishing →
          </button>
        </div>
      )}

      <div style={{ marginTop: "40px", fontSize: "14px", color: "#666" }}>
        <h3>Instructions:</h3>
        <ol>
          <li>Sign in to ArcGIS Online using the sign-in button above.</li>
          <li>
            Enter the Item ID of your Classic Story (Map Tour, Map Journal, Map Series, or
            Cascade)
          </li>
          <li>
            Click Convert to transform your classic story into the new format
          </li>
          <li>Review the converted story and publish when ready</li>
        </ol>
      </div>
    </div>
  );
}