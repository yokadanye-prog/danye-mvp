const mealLabels = {
  breakfast: "早餐",
  lunch: "午餐",
  dinner: "晚餐",
  snack: "加餐",
};

const defaultTargets = {
  mode: "fatLoss",
  calories: 2100,
  protein: 150,
  carbs: 230,
  fat: 65,
  burn: 450,
};

const demoRecord = {
  meals: [
    {
      type: "breakfast",
      label: "早餐",
      confirmed: true,
      foods: [
        { name: "燕麦酸奶碗", grams: 260, kcalPer100: 118, proteinPer100: 7, carbsPer100: 18, fatPer100: 3 },
        { name: "水煮蛋", grams: 100, kcalPer100: 155, proteinPer100: 13, carbsPer100: 1, fatPer100: 11 },
      ],
    },
    {
      type: "lunch",
      label: "午餐",
      confirmed: true,
      foods: [
        { name: "鸡胸肉", grams: 180, kcalPer100: 165, proteinPer100: 31, carbsPer100: 0, fatPer100: 4 },
        { name: "糙米饭", grams: 180, kcalPer100: 116, proteinPer100: 3, carbsPer100: 24, fatPer100: 1 },
        { name: "西兰花", grams: 160, kcalPer100: 35, proteinPer100: 3, carbsPer100: 7, fatPer100: 0 },
      ],
    },
  ],
  exercises: [{ type: "力量训练", minutes: 50, intensity: "中", calories: 430 }],
};

const storageKey = "fitcal-local-state-v1";
const todayKey = localDateKey(new Date());
const savedState = loadSavedState();
const initialDate = isDateKey(savedState?.selectedDate) ? savedState.selectedDate : todayKey;
const initialRecords = loadRecords(savedState);

const state = {
  targets: { ...defaultTargets, ...(savedState?.targets || {}) },
  selectedDate: initialDate,
  records: initialRecords,
  meals: [],
  exercises: [],
  detectedFoods: [],
};

let timelineMonth = startOfMonth(parseDateKey(initialDate));
let editingMealIndex = null;
let editingExerciseIndex = null;
let selectedImageDataUrl = "";

activateRecord(initialDate);

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateKey(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function isDateKey(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value || "");
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addDays(date, amount) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount);
}

function loadSavedState() {
  try {
    return JSON.parse(window.localStorage.getItem(storageKey));
  } catch {
    return null;
  }
}

function loadRecords(saved) {
  if (saved?.records && typeof saved.records === "object") return saved.records;
  if (saved && (Array.isArray(saved.meals) || Array.isArray(saved.exercises))) {
    return {
      [todayKey]: {
        meals: Array.isArray(saved.meals) ? saved.meals : [],
        exercises: Array.isArray(saved.exercises) ? saved.exercises : [],
      },
    };
  }
  return { [todayKey]: deepClone(demoRecord) };
}

function activateRecord(dateKey) {
  const record = state.records[dateKey] || { meals: [], exercises: [] };
  if (!Array.isArray(record.meals)) record.meals = [];
  if (!Array.isArray(record.exercises)) record.exercises = [];
  state.selectedDate = dateKey;
  state.meals = record.meals;
  state.exercises = record.exercises;
}

function persistState() {
  const activeRecord = { meals: state.meals, exercises: state.exercises };
  if (isRecordNonEmpty(activeRecord)) state.records[state.selectedDate] = activeRecord;
  else delete state.records[state.selectedDate];
  window.localStorage.setItem(
    storageKey,
    JSON.stringify({ targets: state.targets, selectedDate: state.selectedDate, records: state.records }),
  );
  document.getElementById("syncButton").textContent = "本机已保存";
}

function commitState() {
  persistState();
  render();
}

function selectDate(dateKey) {
  activateRecord(dateKey);
  timelineMonth = startOfMonth(parseDateKey(dateKey));
  editingMealIndex = null;
  editingExerciseIndex = null;
  resetExerciseForm();
  persistState();
  render();
}

function sumFood(food, key) {
  const per100 = Number(food[`${key}Per100`]) || 0;
  return ((Number(food.grams) || 0) / 100) * per100;
}

function mealTotals(meal) {
  return meal.foods.reduce(
    (acc, food) => {
      acc.calories += sumFood(food, "kcal");
      acc.protein += sumFood(food, "protein");
      acc.carbs += sumFood(food, "carbs");
      acc.fat += sumFood(food, "fat");
      return acc;
    },
    { calories: 0, protein: 0, carbs: 0, fat: 0 },
  );
}

function totalsForRecord(record) {
  const meals = record?.meals || [];
  const exercises = record?.exercises || [];
  const nutrition = meals.reduce(
    (acc, meal) => {
      const totals = mealTotals(meal);
      acc.calories += totals.calories;
      acc.protein += totals.protein;
      acc.carbs += totals.carbs;
      acc.fat += totals.fat;
      return acc;
    },
    { calories: 0, protein: 0, carbs: 0, fat: 0 },
  );
  const burn = exercises.reduce((sum, exercise) => sum + (Number(exercise.calories) || 0), 0);
  return { ...nutrition, burn, balance: nutrition.calories - state.targets.calories - burn };
}

function dayTotals() {
  return totalsForRecord({ meals: state.meals, exercises: state.exercises });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function scoreForRecord(record) {
  const meals = record?.meals || [];
  const exercises = record?.exercises || [];
  const totals = totalsForRecord(record);
  if (!meals.length && !exercises.length) {
    return {
      score: 0,
      confidence: "低可信 · 当天还没有记录",
      parts: [
        { label: "热量目标达成", value: 0, max: 34, note: "等待饮食记录" },
        { label: "营养均衡", value: 0, max: 34, note: "等待营养数据" },
        { label: "三餐结构", value: 0, max: 14, note: "等待餐食记录" },
        { label: "运动消耗", value: 0, max: 18, note: "等待运动记录" },
      ],
    };
  }
  const target = state.targets;
  const calorieGap = Math.abs(totals.calories - target.calories);
  const calorieScore = clamp(34 - (calorieGap / target.calories) * 42, 10, 34);
  const proteinScore = clamp((totals.protein / target.protein) * 22, 6, 22);
  const macroBalance = Math.min(totals.carbs / target.carbs, 1.15) + Math.min(totals.fat / target.fat, 1.15);
  const macroScore = clamp(proteinScore + macroBalance * 7, 8, 34);
  const mealScore = meals.length >= 3 ? 14 : meals.length === 2 ? 10 : 6;
  const activityScore = clamp((totals.burn / target.burn) * 18, 4, 18);
  const score = Math.round(calorieScore + macroScore + mealScore + activityScore);
  const confidence = meals.length >= 3 && exercises.length ? "高可信 · 三餐和运动已确认" : "低可信 · 数据未完整确认";
  return {
    score: clamp(score, 0, 100),
    confidence,
    parts: [
      { label: "热量目标达成", value: Math.round(calorieScore), max: 34, note: calorieGap < 250 ? "接近当天目标" : "与目标差距较大" },
      { label: "营养均衡", value: Math.round(macroScore), max: 34, note: totals.protein >= target.protein ? "蛋白质达标" : "蛋白质仍需补足" },
      { label: "三餐结构", value: mealScore, max: 14, note: meals.length >= 3 ? "三餐完整" : "当天餐食未完整" },
      { label: "运动消耗", value: Math.round(activityScore), max: 18, note: totals.burn >= target.burn ? "运动消耗达标" : "还差一点达到目标" },
    ],
  };
}

function calculateScore() {
  return scoreForRecord({ meals: state.meals, exercises: state.exercises });
}

function formatNumber(value) {
  return Math.round(value).toLocaleString("zh-CN");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}

function isRecordNonEmpty(record) {
  return Boolean(record && ((record.meals || []).length || (record.exercises || []).length));
}

function renderDateNavigator() {
  const selected = parseDateKey(state.selectedDate);
  const isToday = state.selectedDate === todayKey;
  document.getElementById("selectedDateLabel").textContent = isToday
    ? `今日 · ${selected.getMonth() + 1}月${selected.getDate()}日`
    : selected.toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "short" });
  document.getElementById("monthLabel").textContent = `${timelineMonth.getFullYear()}年${timelineMonth.getMonth() + 1}月`;
  document.getElementById("todayButton").hidden = isToday;

  const daysInMonth = new Date(timelineMonth.getFullYear(), timelineMonth.getMonth() + 1, 0).getDate();
  const weekNames = ["日", "一", "二", "三", "四", "五", "六"];
  document.getElementById("dayTrack").innerHTML = Array.from({ length: daysInMonth }, (_, index) => {
    const date = new Date(timelineMonth.getFullYear(), timelineMonth.getMonth(), index + 1);
    const key = localDateKey(date);
    const active = key === state.selectedDate;
    const hasData = isRecordNonEmpty(state.records[key]);
    return `
      <button class="day-button${active ? " active" : ""}" data-date="${key}" type="button" role="listitem" aria-pressed="${active}">
        <span>周${weekNames[date.getDay()]}</span>
        <strong>${date.getDate()}</strong>
        <i class="record-dot${hasData ? " visible" : ""}" aria-hidden="true"></i>
      </button>
    `;
  }).join("");

  requestAnimationFrame(() => {
    document.querySelector(".day-button.active")?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  });
}

function renderMacros(totals) {
  const macros = [
    { label: "蛋白质", value: totals.protein, target: state.targets.protein, unit: "g", color: "var(--green)" },
    { label: "碳水", value: totals.carbs, target: state.targets.carbs, unit: "g", color: "var(--blue)" },
    { label: "脂肪", value: totals.fat, target: state.targets.fat, unit: "g", color: "var(--coral)" },
  ];
  document.getElementById("macroStatus").textContent = totals.protein >= state.targets.protein ? "结构良好" : "蛋白质偏低";
  document.getElementById("macroList").innerHTML = macros.map((macro) => {
    const percent = clamp((macro.value / macro.target) * 100, 0, 120);
    return `
      <div class="macro-row">
        <div class="macro-meta"><strong>${macro.label}</strong><span>${formatNumber(macro.value)} / ${macro.target}${macro.unit}</span></div>
        <div class="bar"><div class="bar-fill" style="--value:${percent}%; --color:${macro.color}"></div></div>
      </div>
    `;
  }).join("");
}

function renderAnswers(totals) {
  const enoughFood = totals.calories <= state.targets.calories + 150;
  const enoughExercise = totals.burn >= state.targets.burn;
  const proteinGap = Math.max(0, state.targets.protein - totals.protein);
  const hasData = state.meals.length || state.exercises.length;
  const answers = hasData ? [
    { title: "当天吃多了吗", text: enoughFood ? "摄入仍在目标附近" : "摄入超过目标，下一餐可减少主食", status: enoughFood ? "good" : "warn", tag: enoughFood ? "可控" : "偏高" },
    { title: "运动够了吗", text: enoughExercise ? "已达到当天运动目标" : `还差 ${formatNumber(Math.max(0, state.targets.burn - totals.burn))} kcal`, status: enoughExercise ? "good" : "warn", tag: enoughExercise ? "达标" : "待补" },
    { title: "哪里需要改", text: proteinGap > 0 ? `优先补 ${formatNumber(proteinGap)}g 蛋白质` : "保持当前三餐结构", status: proteinGap > 0 ? "warn" : "good", tag: proteinGap > 0 ? "建议" : "稳定" },
  ] : [
    { title: "当天暂无记录", text: "添加餐食或运动后生成总结", status: "warn", tag: "待记录" },
  ];
  document.getElementById("answerList").innerHTML = answers.map((answer) => `
    <div class="answer ${answer.status}"><div><strong>${answer.title}</strong><p>${answer.text}</p></div><mark>${answer.tag}</mark></div>
  `).join("");
}

function renderTimeline() {
  document.getElementById("mealCount").textContent = `${state.meals.length} 餐已确认`;
  document.getElementById("mealTimeline").innerHTML = state.meals.length ? state.meals.map((meal, index) => {
    const totals = mealTotals(meal);
    const foods = meal.foods.map((food) => escapeHtml(food.name)).join("、");
    return `
      <div class="timeline-row">
        <div><strong>${meal.label}</strong><p>${foods}</p></div>
        <div class="row-actions"><span>${formatNumber(totals.calories)} kcal</span><button class="row-action" type="button" data-edit-meal="${index}">编辑</button><button class="row-action danger" type="button" data-delete-meal="${index}">删除</button></div>
      </div>
    `;
  }).join("") : '<p class="empty-state">当天还没有饮食记录</p>';

  document.getElementById("exerciseTimeline").innerHTML = state.exercises.length ? state.exercises.map((exercise, index) => `
    <div class="timeline-row">
      <div><strong>${escapeHtml(exercise.type)}</strong><p>${exercise.minutes} 分钟 · ${exercise.intensity}强度</p></div>
      <div class="row-actions"><span>${formatNumber(exercise.calories)} kcal</span><button class="row-action" type="button" data-edit-exercise="${index}">编辑</button><button class="row-action danger" type="button" data-delete-exercise="${index}">删除</button></div>
    </div>
  `).join("") : '<p class="empty-state">当天还没有运动记录</p>';
}

function renderTrend() {
  const selected = parseDateKey(state.selectedDate);
  const rows = [-2, -1, 0].map((offset) => {
    const date = addDays(selected, offset);
    const record = state.records[localDateKey(date)] || { meals: [], exercises: [] };
    const totals = totalsForRecord(record);
    return {
      day: offset === 0 ? "所选" : `${date.getMonth() + 1}/${date.getDate()}`,
      intake: totals.calories,
      burn: totals.burn,
      score: scoreForRecord(record).score,
    };
  });
  document.getElementById("trendChart").innerHTML = rows.map((row) => `
    <div class="trend-row">
      <strong>${row.day}</strong>
      <div class="trend-bars"><div class="mini-bar"><span style="--value:${clamp((row.intake / 2600) * 100, 0, 100)}%; --color:var(--coral)"></span></div><div class="mini-bar"><span style="--value:${clamp((row.burn / 700) * 100, 0, 100)}%; --color:var(--green)"></span></div></div>
      <strong>${Math.round(row.score)}分</strong>
    </div>
  `).join("");
  const recordedDays = rows.filter((row) => row.intake || row.burn).length;
  document.getElementById("trendInsights").innerHTML = `
    <div class="answer ${recordedDays >= 3 ? "good" : "warn"}"><div><strong>连续记录</strong><p>近 3 天已有 ${recordedDays} 天数据</p></div><mark>${recordedDays >= 3 ? "稳定" : "继续"}</mark></div>
    <div class="answer warn"><div><strong>训练日建议</strong><p>高强度训练日优先补足蛋白质，再调整碳水</p></div><mark>参考</mark></div>
  `;
}

function renderScoreDialog(scoreData) {
  document.getElementById("scoreBreakdown").innerHTML = scoreData.parts.map((part) => `
    <div class="score-part"><div><strong>${part.label}</strong><p>${part.note}</p></div><span>${part.value}/${part.max}</span></div>
  `).join("");
}

function render() {
  const totals = dayTotals();
  const scoreData = calculateScore();
  renderDateNavigator();
  document.getElementById("healthScore").textContent = scoreData.score;
  document.getElementById("confidenceText").textContent = scoreData.confidence;
  document.getElementById("intakeMetric").textContent = formatNumber(totals.calories);
  document.getElementById("burnMetric").textContent = formatNumber(totals.burn);
  document.getElementById("balanceMetric").textContent = `${totals.balance > 0 ? "+" : ""}${formatNumber(totals.balance)}`;
  renderMacros(totals);
  renderAnswers(totals);
  renderTimeline();
  renderTrend();
  renderScoreDialog(scoreData);
  document.getElementById("goalMode").value = state.targets.mode;
  document.getElementById("calorieTarget").value = state.targets.calories;
  document.getElementById("proteinTarget").value = state.targets.protein;
  document.getElementById("burnTarget").value = state.targets.burn;
}

function renderDetectedFoods() {
  document.getElementById("detectedFoods").innerHTML = state.detectedFoods.map((food, index) => `
    <div class="food-row">
      <div><strong>${escapeHtml(food.name)}</strong><small>${formatNumber(sumFood(food, "kcal"))} kcal · ${formatNumber(sumFood(food, "protein"))}g 蛋白质</small></div>
      <label><span class="sr-only">${escapeHtml(food.name)} 份量</span><input type="number" min="1" max="2000" value="${food.grams}" data-food-index="${index}" aria-label="${escapeHtml(food.name)} 克数" /></label>
    </div>
  `).join("");
}

function estimateExercise() {
  const minutes = Number(document.getElementById("exerciseMinutes").value);
  const factor = Number(document.getElementById("exerciseIntensity").value);
  return Math.round(minutes * factor * 70);
}

function foodEditorRow(food = {}) {
  const values = { name: food.name || "", grams: food.grams || 100, kcalPer100: food.kcalPer100 || 0, proteinPer100: food.proteinPer100 || 0, carbsPer100: food.carbsPer100 || 0, fatPer100: food.fatPer100 || 0 };
  return `
    <div class="food-editor" data-editor-food>
      <label>食物名称<input data-field="name" value="${escapeHtml(values.name)}" required /></label>
      <label>份量(g)<input data-field="grams" type="number" min="1" value="${values.grams}" required /></label>
      <label>热量/100g<input data-field="kcalPer100" type="number" min="0" value="${values.kcalPer100}" required /></label>
      <label>蛋白/100g<input data-field="proteinPer100" type="number" min="0" value="${values.proteinPer100}" required /></label>
      <label>碳水/100g<input data-field="carbsPer100" type="number" min="0" value="${values.carbsPer100}" required /></label>
      <label>脂肪/100g<input data-field="fatPer100" type="number" min="0" value="${values.fatPer100}" required /></label>
      <button class="row-action danger remove-food" type="button" data-remove-food>删除这项食物</button>
    </div>
  `;
}

function openMealEditor(index = null) {
  editingMealIndex = index;
  const meal = index === null ? null : state.meals[index];
  document.getElementById("mealDialogTitle").textContent = meal ? `编辑${meal.label}` : "新增一餐";
  document.getElementById("editorMealType").value = meal?.type || "dinner";
  document.getElementById("editorFoods").innerHTML = (meal?.foods || [{}]).map(foodEditorRow).join("");
  document.getElementById("mealDialog").showModal();
}

function closeMealEditor() {
  editingMealIndex = null;
  document.getElementById("mealDialog").close();
}

function readMealEditorFoods() {
  return [...document.querySelectorAll("[data-editor-food]")].map((row) => {
    const value = (field) => row.querySelector(`[data-field="${field}"]`).value;
    return { name: value("name").trim(), grams: Number(value("grams")), kcalPer100: Number(value("kcalPer100")), proteinPer100: Number(value("proteinPer100")), carbsPer100: Number(value("carbsPer100")), fatPer100: Number(value("fatPer100")) };
  }).filter((food) => food.name && food.grams > 0);
}

function resetExerciseForm() {
  editingExerciseIndex = null;
  document.getElementById("exerciseForm").reset();
  document.getElementById("exerciseMinutes").value = 45;
  document.getElementById("exerciseIntensity").value = "0.11";
  document.getElementById("exerciseEstimate").textContent = `预计 ${estimateExercise()} kcal`;
  document.getElementById("saveExerciseButton").textContent = "保存运动";
  document.getElementById("cancelExerciseEdit").hidden = true;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("无法读取照片"));
    reader.readAsDataURL(file);
  });
}

function loadImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("照片格式无法识别"));
    image.src = dataUrl;
  });
}

async function compressMealPhoto(file) {
  const source = await readFileAsDataUrl(file);
  const image = await loadImage(source);
  const maxSide = 1024;
  const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
  canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.78);
}

function setRecognitionStatus(message, type = "") {
  const status = document.getElementById("recognitionStatus");
  status.textContent = message;
  status.dataset.type = type;
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".screen").forEach((screen) => screen.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.target).classList.add("active");
  });
});

document.getElementById("dayTrack").addEventListener("click", (event) => {
  const button = event.target.closest("[data-date]");
  if (button) selectDate(button.dataset.date);
});

document.getElementById("previousMonthButton").addEventListener("click", () => {
  const month = new Date(timelineMonth.getFullYear(), timelineMonth.getMonth() - 1, 1);
  selectDate(localDateKey(month));
});

document.getElementById("nextMonthButton").addEventListener("click", () => {
  const month = new Date(timelineMonth.getFullYear(), timelineMonth.getMonth() + 1, 1);
  selectDate(localDateKey(month));
});

document.getElementById("todayButton").addEventListener("click", () => selectDate(todayKey));

document.getElementById("choosePhotoButton").addEventListener("click", () => document.getElementById("mealPhotoInput").click());

document.getElementById("mealPhotoInput").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    setRecognitionStatus("正在处理照片…");
    selectedImageDataUrl = await compressMealPhoto(file);
    document.getElementById("mealPhotoPreview").src = selectedImageDataUrl;
    document.getElementById("photoTitle").textContent = file.name || "待识别餐食";
    document.getElementById("recognizeButton").disabled = false;
    document.getElementById("recognitionPanel").hidden = true;
    setRecognitionStatus("照片已就绪，可以开始识别", "success");
  } catch (error) {
    selectedImageDataUrl = "";
    document.getElementById("recognizeButton").disabled = true;
    setRecognitionStatus(error.message || "照片处理失败", "error");
  }
});

document.getElementById("recognizeButton").addEventListener("click", async () => {
  if (!selectedImageDataUrl) return;
  const button = document.getElementById("recognizeButton");
  button.disabled = true;
  button.textContent = "识别中…";
  setRecognitionStatus("AI 正在分析食物和估算份量…");
  try {
    const response = await fetch("/api/recognize-meal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: selectedImageDataUrl }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "识别服务暂时不可用");
    state.detectedFoods = Array.isArray(result.foods) ? result.foods : [];
    if (!state.detectedFoods.length) throw new Error("照片中没有识别到明确的食物");
    document.getElementById("recognitionPanel").hidden = false;
    document.getElementById("recognitionNote").textContent = `${result.note || "份量和营养为估算值，请确认后保存"} · 置信度 ${Math.round((result.confidence || 0) * 100)}%`;
    renderDetectedFoods();
    setRecognitionStatus(`已识别 ${state.detectedFoods.length} 项食物，请校准份量`, "success");
  } catch (error) {
    setRecognitionStatus(error.message || "识别失败，请稍后重试", "error");
  } finally {
    button.disabled = false;
    button.textContent = "重新识别";
  }
});

document.getElementById("detectedFoods").addEventListener("change", (event) => {
  const input = event.target.closest("[data-food-index]");
  if (!input) return;
  state.detectedFoods[Number(input.dataset.foodIndex)].grams = Number(input.value);
  renderDetectedFoods();
});

document.getElementById("saveMealButton").addEventListener("click", () => {
  if (!state.detectedFoods.length) return;
  const type = document.getElementById("mealType").value;
  const meal = { type, label: mealLabels[type], confirmed: true, foods: state.detectedFoods.map((food) => ({ ...food })) };
  const existingIndex = state.meals.findIndex((item) => item.type === type);
  if (existingIndex >= 0) state.meals.splice(existingIndex, 1, meal);
  else state.meals.push(meal);
  state.detectedFoods = [];
  selectedImageDataUrl = "";
  document.getElementById("recognitionPanel").hidden = true;
  document.getElementById("mealPhotoInput").value = "";
  document.getElementById("recognizeButton").disabled = true;
  document.getElementById("recognizeButton").textContent = "识别食物与热量";
  document.getElementById("photoTitle").textContent = "选择一张餐食照片";
  setRecognitionStatus("餐食已保存到所选日期", "success");
  commitState();
});

["exerciseMinutes", "exerciseIntensity"].forEach((id) => {
  document.getElementById(id).addEventListener("input", () => {
    document.getElementById("exerciseEstimate").textContent = `预计 ${estimateExercise()} kcal`;
  });
});

document.getElementById("exerciseForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const intensityLabel = document.getElementById("exerciseIntensity").selectedOptions[0].textContent;
  const exercise = { type: document.getElementById("exerciseType").value, minutes: Number(document.getElementById("exerciseMinutes").value), intensity: intensityLabel, calories: estimateExercise() };
  if (editingExerciseIndex === null) state.exercises.unshift(exercise);
  else state.exercises.splice(editingExerciseIndex, 1, exercise);
  resetExerciseForm();
  commitState();
});

document.getElementById("goalMode").addEventListener("change", (event) => {
  state.targets.mode = event.target.value;
  if (event.target.value === "muscleGain") state.targets.calories = 2550;
  if (event.target.value === "maintain") state.targets.calories = 2300;
  if (event.target.value === "fatLoss") state.targets.calories = 2100;
  document.getElementById("calorieTarget").value = state.targets.calories;
  commitState();
});

[["calorieTarget", "calories"], ["proteinTarget", "protein"], ["burnTarget", "burn"]].forEach(([id, key]) => {
  document.getElementById(id).addEventListener("input", (event) => {
    state.targets[key] = Number(event.target.value);
    commitState();
  });
});

document.getElementById("syncButton").addEventListener("click", () => {
  persistState();
  document.getElementById("syncTime").textContent = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
});

document.getElementById("addMealButton").addEventListener("click", () => openMealEditor());
document.getElementById("closeMealDialog").addEventListener("click", closeMealEditor);
document.getElementById("addFoodButton").addEventListener("click", () => document.getElementById("editorFoods").insertAdjacentHTML("beforeend", foodEditorRow()));

document.getElementById("editorFoods").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-food]");
  if (!button || document.querySelectorAll("[data-editor-food]").length === 1) return;
  button.closest("[data-editor-food]").remove();
});

document.getElementById("mealEditorForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const foods = readMealEditorFoods();
  if (!foods.length) return;
  const type = document.getElementById("editorMealType").value;
  const meal = { type, label: mealLabels[type], confirmed: true, foods };
  if (editingMealIndex !== null) state.meals.splice(editingMealIndex, 1, meal);
  else {
    const existing = state.meals.findIndex((item) => item.type === type);
    if (existing >= 0) state.meals[existing].foods.push(...foods);
    else state.meals.push(meal);
  }
  closeMealEditor();
  commitState();
});

document.getElementById("mealTimeline").addEventListener("click", (event) => {
  const edit = event.target.closest("[data-edit-meal]");
  const remove = event.target.closest("[data-delete-meal]");
  if (edit) openMealEditor(Number(edit.dataset.editMeal));
  if (remove && window.confirm("删除这餐记录？")) {
    state.meals.splice(Number(remove.dataset.deleteMeal), 1);
    commitState();
  }
});

document.getElementById("exerciseTimeline").addEventListener("click", (event) => {
  const edit = event.target.closest("[data-edit-exercise]");
  const remove = event.target.closest("[data-delete-exercise]");
  if (edit) {
    editingExerciseIndex = Number(edit.dataset.editExercise);
    const exercise = state.exercises[editingExerciseIndex];
    document.getElementById("exerciseType").value = exercise.type;
    document.getElementById("exerciseMinutes").value = exercise.minutes;
    document.getElementById("exerciseIntensity").value = { 低: "0.08", 中: "0.11", 高: "0.15" }[exercise.intensity] || "0.11";
    document.getElementById("exerciseEstimate").textContent = `预计 ${estimateExercise()} kcal`;
    document.getElementById("saveExerciseButton").textContent = "更新运动";
    document.getElementById("cancelExerciseEdit").hidden = false;
  }
  if (remove && window.confirm("删除这条运动记录？")) {
    state.exercises.splice(Number(remove.dataset.deleteExercise), 1);
    commitState();
  }
});

document.getElementById("cancelExerciseEdit").addEventListener("click", resetExerciseForm);
document.getElementById("resetDataButton").addEventListener("click", () => {
  if (!window.confirm("恢复演示数据会删除当前浏览器中的记录，继续吗？")) return;
  state.targets = { ...defaultTargets };
  state.records = { [todayKey]: deepClone(demoRecord) };
  timelineMonth = startOfMonth(new Date());
  activateRecord(todayKey);
  resetExerciseForm();
  commitState();
});

document.getElementById("scoreExplainButton").addEventListener("click", () => document.getElementById("scoreDialog").showModal());
document.getElementById("closeDialog").addEventListener("click", () => document.getElementById("scoreDialog").close());

render();

