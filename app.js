const state = {
  targets: {
    mode: "fatLoss",
    calories: 2100,
    protein: 150,
    carbs: 230,
    fat: 65,
    burn: 450,
  },
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
  detectedFoods: [],
};

const mealLabels = {
  breakfast: "早餐",
  lunch: "午餐",
  dinner: "晚餐",
  snack: "加餐",
};

const recognitionPreset = [
  { name: "三文鱼", grams: 140, kcalPer100: 208, proteinPer100: 20, carbsPer100: 0, fatPer100: 13 },
  { name: "藜麦", grams: 130, kcalPer100: 120, proteinPer100: 4, carbsPer100: 21, fatPer100: 2 },
  { name: "芦笋", grams: 120, kcalPer100: 22, proteinPer100: 2, carbsPer100: 4, fatPer100: 0 },
];

const trendBase = [
  { day: "周五", intake: 2240, burn: 320, score: 74 },
  { day: "周六", intake: 1960, burn: 520, score: 89 },
];

function sumFood(food, key) {
  const per100 = food[`${key}Per100`];
  return (food.grams / 100) * per100;
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

function dayTotals() {
  const nutrition = state.meals.reduce(
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
  const burn = state.exercises.reduce((sum, exercise) => sum + exercise.calories, 0);
  return { ...nutrition, burn, balance: nutrition.calories - state.targets.calories - burn };
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function calculateScore() {
  const totals = dayTotals();
  const target = state.targets;
  const calorieGap = Math.abs(totals.calories - target.calories);
  const calorieScore = clamp(34 - (calorieGap / target.calories) * 42, 10, 34);
  const proteinScore = clamp((totals.protein / target.protein) * 22, 6, 22);
  const macroBalance = Math.min(totals.carbs / target.carbs, 1.15) + Math.min(totals.fat / target.fat, 1.15);
  const macroScore = clamp(proteinScore + macroBalance * 7, 8, 34);
  const mealScore = state.meals.length >= 3 ? 14 : state.meals.length === 2 ? 10 : 6;
  const activityScore = clamp((totals.burn / target.burn) * 18, 4, 18);
  const score = Math.round(calorieScore + macroScore + mealScore + activityScore);
  const confidence = state.meals.length >= 3 && state.exercises.length ? "高可信 · 三餐和运动已确认" : "低可信 · 数据未完整确认";

  return {
    score: clamp(score, 0, 100),
    confidence,
    parts: [
      { label: "热量目标达成", value: Math.round(calorieScore), max: 34, note: calorieGap < 250 ? "接近今日目标" : "与目标差距较大" },
      { label: "营养均衡", value: Math.round(macroScore), max: 34, note: totals.protein >= target.protein ? "蛋白质达标" : "蛋白质仍需补足" },
      { label: "三餐结构", value: mealScore, max: 14, note: state.meals.length >= 3 ? "三餐完整" : "晚餐或加餐未确认" },
      { label: "运动消耗", value: Math.round(activityScore), max: 18, note: totals.burn >= target.burn ? "运动消耗达标" : "还差一点达到目标" },
    ],
  };
}

function formatNumber(value) {
  return Math.round(value).toLocaleString("zh-CN");
}

function renderMacros(totals) {
  const macros = [
    { label: "蛋白质", value: totals.protein, target: state.targets.protein, unit: "g", color: "var(--green)" },
    { label: "碳水", value: totals.carbs, target: state.targets.carbs, unit: "g", color: "var(--blue)" },
    { label: "脂肪", value: totals.fat, target: state.targets.fat, unit: "g", color: "var(--coral)" },
  ];
  document.getElementById("macroStatus").textContent =
    totals.protein >= state.targets.protein ? "结构良好" : "蛋白质偏低";
  document.getElementById("macroList").innerHTML = macros
    .map((macro) => {
      const percent = clamp((macro.value / macro.target) * 100, 0, 120);
      return `
        <div class="macro-row">
          <div class="macro-meta">
            <strong>${macro.label}</strong>
            <span>${formatNumber(macro.value)} / ${macro.target}${macro.unit}</span>
          </div>
          <div class="bar"><div class="bar-fill" style="--value:${percent}%; --color:${macro.color}"></div></div>
        </div>
      `;
    })
    .join("");
}

function renderAnswers(totals) {
  const enoughFood = totals.calories <= state.targets.calories + 150;
  const enoughExercise = totals.burn >= state.targets.burn;
  const proteinGap = Math.max(0, state.targets.protein - totals.protein);
  const answers = [
    {
      title: "今天吃多了吗",
      text: enoughFood ? "摄入仍在目标附近" : "摄入超过目标，晚餐可减主食",
      status: enoughFood ? "good" : "warn",
      tag: enoughFood ? "可控" : "偏高",
    },
    {
      title: "运动够了吗",
      text: enoughExercise ? "已接近训练日消耗" : `还差 ${formatNumber(state.targets.burn - totals.burn)} kcal`,
      status: enoughExercise ? "good" : "warn",
      tag: enoughExercise ? "达标" : "待补",
    },
    {
      title: "哪里需要改",
      text: proteinGap > 0 ? `优先补 ${formatNumber(proteinGap)}g 蛋白质` : "保持当前三餐结构",
      status: proteinGap > 0 ? "warn" : "good",
      tag: proteinGap > 0 ? "建议" : "稳定",
    },
  ];
  document.getElementById("answerList").innerHTML = answers
    .map(
      (answer) => `
        <div class="answer ${answer.status}">
          <div>
            <strong>${answer.title}</strong>
            <p>${answer.text}</p>
          </div>
          <mark>${answer.tag}</mark>
        </div>
      `,
    )
    .join("");
}

function renderTimeline() {
  document.getElementById("mealCount").textContent = `${state.meals.length} 餐已确认`;
  document.getElementById("mealTimeline").innerHTML = state.meals
    .map((meal) => {
      const totals = mealTotals(meal);
      const foods = meal.foods.map((food) => food.name).join("、");
      return `
        <div class="timeline-row">
          <div>
            <strong>${meal.label}</strong>
            <p>${foods}</p>
          </div>
          <span>${formatNumber(totals.calories)} kcal</span>
        </div>
      `;
    })
    .join("");

  document.getElementById("exerciseTimeline").innerHTML = state.exercises
    .map(
      (exercise) => `
        <div class="timeline-row">
          <div>
            <strong>${exercise.type}</strong>
            <p>${exercise.minutes} 分钟 · ${exercise.intensity}强度</p>
          </div>
          <span>${formatNumber(exercise.calories)} kcal</span>
        </div>
      `,
    )
    .join("");
}

function renderTrend(totals, score) {
  const rows = [...trendBase, { day: "今天", intake: totals.calories, burn: totals.burn, score }];
  document.getElementById("trendChart").innerHTML = rows
    .map(
      (row) => `
        <div class="trend-row">
          <strong>${row.day}</strong>
          <div class="trend-bars">
            <div class="mini-bar"><span style="--value:${clamp((row.intake / 2600) * 100, 8, 100)}%; --color:var(--coral)"></span></div>
            <div class="mini-bar"><span style="--value:${clamp((row.burn / 700) * 100, 8, 100)}%; --color:var(--green)"></span></div>
          </div>
          <strong>${Math.round(row.score)}分</strong>
        </div>
      `,
    )
    .join("");

  document.getElementById("trendInsights").innerHTML = `
    <div class="answer good">
      <div><strong>连续记录</strong><p>已形成 3 天摄入与消耗趋势</p></div><mark>稳定</mark>
    </div>
    <div class="answer warn">
      <div><strong>训练日建议</strong><p>高强度训练日优先补足蛋白质，再调整碳水</p></div><mark>参考</mark>
    </div>
  `;
}

function renderScoreDialog(scoreData) {
  document.getElementById("scoreBreakdown").innerHTML = scoreData.parts
    .map(
      (part) => `
        <div class="score-part">
          <div>
            <strong>${part.label}</strong>
            <p>${part.note}</p>
          </div>
          <span>${part.value}/${part.max}</span>
        </div>
      `,
    )
    .join("");
}

function render() {
  const totals = dayTotals();
  const scoreData = calculateScore();
  document.getElementById("healthScore").textContent = scoreData.score;
  document.getElementById("confidenceText").textContent = scoreData.confidence;
  document.getElementById("intakeMetric").textContent = formatNumber(totals.calories);
  document.getElementById("burnMetric").textContent = formatNumber(totals.burn);
  document.getElementById("balanceMetric").textContent = `${totals.balance > 0 ? "+" : ""}${formatNumber(totals.balance)}`;
  renderMacros(totals);
  renderAnswers(totals);
  renderTimeline();
  renderTrend(totals, scoreData.score);
  renderScoreDialog(scoreData);
}

function renderDetectedFoods() {
  document.getElementById("detectedFoods").innerHTML = state.detectedFoods
    .map(
      (food, index) => `
        <div class="food-row">
          <div>
            <strong>${food.name}</strong>
            <small>${formatNumber(sumFood(food, "kcal"))} kcal · ${formatNumber(sumFood(food, "protein"))}g 蛋白质</small>
          </div>
          <input type="number" min="20" max="600" value="${food.grams}" data-food-index="${index}" aria-label="${food.name} 克数" />
        </div>
      `,
    )
    .join("");
}

function estimateExercise() {
  const minutes = Number(document.getElementById("exerciseMinutes").value);
  const factor = Number(document.getElementById("exerciseIntensity").value);
  return Math.round(minutes * factor * 70);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".screen").forEach((screen) => screen.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.target).classList.add("active");
  });
});

document.getElementById("recognizeButton").addEventListener("click", () => {
  state.detectedFoods = recognitionPreset.map((food) => ({ ...food }));
  document.getElementById("recognitionPanel").hidden = false;
  renderDetectedFoods();
});

document.getElementById("detectedFoods").addEventListener("input", (event) => {
  const input = event.target.closest("[data-food-index]");
  if (!input) return;
  state.detectedFoods[Number(input.dataset.foodIndex)].grams = Number(input.value);
  renderDetectedFoods();
});

document.getElementById("saveMealButton").addEventListener("click", () => {
  if (!state.detectedFoods.length) return;
  const type = document.getElementById("mealType").value;
  const meal = {
    type,
    label: mealLabels[type],
    confirmed: true,
    foods: state.detectedFoods.map((food) => ({ ...food })),
  };
  const existingIndex = state.meals.findIndex((item) => item.type === type);
  if (existingIndex >= 0) state.meals.splice(existingIndex, 1, meal);
  else state.meals.push(meal);
  state.detectedFoods = [];
  document.getElementById("recognitionPanel").hidden = true;
  render();
});

["exerciseMinutes", "exerciseIntensity"].forEach((id) => {
  document.getElementById(id).addEventListener("input", () => {
    document.getElementById("exerciseEstimate").textContent = `预计 ${estimateExercise()} kcal`;
  });
});

document.getElementById("exerciseForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const intensityLabel = document.getElementById("exerciseIntensity").selectedOptions[0].textContent;
  state.exercises.unshift({
    type: document.getElementById("exerciseType").value,
    minutes: Number(document.getElementById("exerciseMinutes").value),
    intensity: intensityLabel,
    calories: estimateExercise(),
  });
  render();
});

document.getElementById("goalMode").addEventListener("change", (event) => {
  state.targets.mode = event.target.value;
  if (event.target.value === "muscleGain") state.targets.calories = 2550;
  if (event.target.value === "maintain") state.targets.calories = 2300;
  if (event.target.value === "fatLoss") state.targets.calories = 2100;
  document.getElementById("calorieTarget").value = state.targets.calories;
  render();
});

[
  ["calorieTarget", "calories"],
  ["proteinTarget", "protein"],
  ["burnTarget", "burn"],
].forEach(([id, key]) => {
  document.getElementById(id).addEventListener("input", (event) => {
    state.targets[key] = Number(event.target.value);
    render();
  });
});

document.getElementById("cloudSync").addEventListener("change", (event) => {
  document.getElementById("syncButton").textContent = event.target.checked ? "云端已同步" : "仅本机记录";
});

document.getElementById("photoStorage").addEventListener("change", (event) => {
  document.getElementById("syncTime").textContent = event.target.checked ? "照片已授权" : "18:42";
});

document.getElementById("syncButton").addEventListener("click", () => {
  const now = new Date();
  document.getElementById("syncTime").textContent = now.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
});

document.getElementById("scoreExplainButton").addEventListener("click", () => {
  document.getElementById("scoreDialog").showModal();
});

document.getElementById("closeDialog").addEventListener("click", () => {
  document.getElementById("scoreDialog").close();
});

render();

