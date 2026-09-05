const MAX_IMAGE_LENGTH = 2_500_000;
const ALLOWED_IMAGE = /^data:image\/(jpeg|png|webp);base64,/;

function sendJson(response, status, body) {
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");
  response.status(status).json(body);
}

function extractOutputText(result) {
  for (const item of result.output || []) {
    for (const content of item.content || []) {
      if (content.type === "output_text" && content.text) return content.text;
    }
  }
  return "";
}

module.exports = async function recognizeMeal(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return sendJson(response, 405, { error: "仅支持 POST 请求" });
  }

  if (!process.env.OPENAI_API_KEY) {
    return sendJson(response, 503, { error: "识别服务尚未配置，请联系管理员添加 OPENAI_API_KEY" });
  }

  const image = request.body?.image;
  if (typeof image !== "string" || !ALLOWED_IMAGE.test(image)) {
    return sendJson(response, 400, { error: "请上传 JPEG、PNG 或 WebP 餐食照片" });
  }
  if (image.length > MAX_IMAGE_LENGTH) {
    return sendJson(response, 413, { error: "照片过大，请压缩后重试" });
  }

  try {
    const openaiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        store: false,
        max_output_tokens: 900,
        input: [
          {
            role: "developer",
            content: [
              {
                type: "input_text",
                text: "你是谨慎的餐食图片分析助手。识别清晰可见的食物，并估算可食用部分的克数以及每100克热量、蛋白质、碳水和脂肪。不要输出医疗诊断。无法判断时降低置信度并在说明中明确不确定性。所有食物名称使用简体中文。",
              },
            ],
          },
          {
            role: "user",
            content: [
              { type: "input_text", text: "请分析这张餐食照片。只列出清晰可见且可能被食用的主要食物；调味料只有在明显影响热量时才单独列出。" },
              { type: "input_image", image_url: image, detail: "low" },
            ],
          },
        ],
        text: {
          format: {
            type: "json_schema",
            name: "meal_recognition",
            strict: true,
            schema: {
              type: "object",
              additionalProperties: false,
              properties: {
                foods: {
                  type: "array",
                  minItems: 0,
                  maxItems: 10,
                  items: {
                    type: "object",
                    additionalProperties: false,
                    properties: {
                      name: { type: "string" },
                      grams: { type: "number", minimum: 1, maximum: 2000 },
                      kcalPer100: { type: "number", minimum: 0, maximum: 1000 },
                      proteinPer100: { type: "number", minimum: 0, maximum: 100 },
                      carbsPer100: { type: "number", minimum: 0, maximum: 100 },
                      fatPer100: { type: "number", minimum: 0, maximum: 100 },
                    },
                    required: ["name", "grams", "kcalPer100", "proteinPer100", "carbsPer100", "fatPer100"],
                  },
                },
                confidence: { type: "number", minimum: 0, maximum: 1 },
                note: { type: "string" },
              },
              required: ["foods", "confidence", "note"],
            },
          },
        },
      }),
    });

    const result = await openaiResponse.json();
    if (!openaiResponse.ok) {
      const errorCode = String(result.error?.code || result.error?.type || "").toLowerCase();
      const errorMessage = String(result.error?.message || "").toLowerCase();
      const quotaExhausted = errorCode.includes("quota")
        || errorMessage.includes("quota")
        || errorMessage.includes("billing")
        || errorMessage.includes("credit")
        || errorMessage.includes("balance");
      const status = openaiResponse.status === 401 ? 503 : openaiResponse.status === 429 ? 429 : 502;
      const message = openaiResponse.status === 401
        ? "识别服务密钥无效或已过期，请联系管理员"
        : quotaExhausted
          ? "OpenAI API 当前没有可用额度，请先检查 API 账单或使用限额"
          : openaiResponse.status === 429
            ? "识别请求过于频繁，请稍后重试"
            : "AI 识别服务请求失败，请稍后重试";
      console.error("OpenAI meal recognition failed", openaiResponse.status, result.error?.code || "unknown");
      return sendJson(response, status, { error: message });
    }

    const outputText = extractOutputText(result);
    if (!outputText) return sendJson(response, 502, { error: "AI 未返回可用的识别结果" });
    const parsed = JSON.parse(outputText);
    return sendJson(response, 200, parsed);
  } catch (error) {
    console.error("Meal recognition handler failed", error?.message || "unknown");
    return sendJson(response, 500, { error: "识别过程中发生错误，请稍后重试" });
  }
};

