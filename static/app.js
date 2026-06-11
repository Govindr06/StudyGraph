const authStatus = document.getElementById("auth-status");
const feedback = document.getElementById("feedback");
const scheduleBody = document.getElementById("schedule-body");
const subjectFeedback = document.getElementById("subject-feedback");
const emailForm = document.getElementById("email-form");
const emailFeedback = document.getElementById("email-feedback");
const saveEmailButton = document.getElementById("save-email-button");
const goalForm = document.getElementById("goal-form");
const pushCalendarButton = document.getElementById("push-calendar");
const emailInput = document.getElementById("email");
const topicInput = document.getElementById("topic");
const durationDaysInput = document.getElementById("duration-days");
const focusTopicInput = document.getElementById("focus-topic");
const restDaysInput = document.getElementById("rest-days");
const studyTimeInput = document.getElementById("study-time");
const contentStyleInput = document.getElementById("content-style");
const extraSubjectInput = document.getElementById("extra-subject");
const addSubjectButton = document.getElementById("add-subject");
const clearSubjectButton = document.getElementById("clear-subject");
const calendar = document.getElementById("calendar");
const rewardMessage = document.getElementById("reward-message");
const quoteElem = document.getElementById("motivational-quote");
const newQuoteBtn = document.getElementById("new-quote");
const taskInput = document.getElementById("new-task");
const addTaskBtn = document.getElementById("add-task");
const taskList = document.getElementById("task-list");
const timerDisplay = document.getElementById("timer-display");
const startBtn = document.getElementById("start-timer");
const stopBtn = document.getElementById("stop-timer");
const resetBtn = document.getElementById("reset-timer");
const contentForm = document.getElementById("content-form");
const generateContentButton = document.getElementById("generate-content");
const progressPromptInput = document.getElementById("progress-prompt");
const selectedDayLabel = document.getElementById("selected-day");
const lessonContent = document.getElementById("lesson-content");
const utilityTabs = document.querySelectorAll("[data-utility-target]");
const utilityPanels = document.querySelectorAll(".utility-panel");
const themeToggles = document.querySelectorAll("[data-theme]");

const defaultSubjects = ["Probability", "Automata", "OS", "Management"];
const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const emojis = ["📚", "✏️", "🖊️", "📘", "📝", "📒", "📎"];
const quotes = [
    "You do not need perfect motivation. You need a start.",
    "Consistency makes difficult things become familiar.",
    "A calm plan beats last-minute panic every time.",
    "Small study sessions compound into real expertise.",
    "Progress feels slow until one day it looks obvious."
];

let timerInterval = null;
let elapsedSeconds = 0;
let selectedScheduleId = null;
let selectedScheduleTitle = "";

function getSubjects() {
    const customSubject = (localStorage.getItem("studygraphExtraSubject") || "").trim();
    return customSubject ? [...defaultSubjects, customSubject] : [...defaultSubjects];
}

function setPlannerFeedback(message, tone = "neutral") {
    if (!subjectFeedback) {
        return;
    }
    subjectFeedback.textContent = message;
    subjectFeedback.className = tone === "neutral"
        ? "planner-inline-feedback empty-state"
        : `planner-inline-feedback ${tone}`;
}

function setEmailFeedback(message, tone = "neutral") {
    if (!emailFeedback) {
        return;
    }
    emailFeedback.textContent = message;
    emailFeedback.className = tone === "neutral"
        ? "planner-inline-feedback empty-state"
        : `planner-inline-feedback ${tone}`;
}

function syncSubjectControls() {
    if (!extraSubjectInput) {
        return;
    }
    const customSubject = (localStorage.getItem("studygraphExtraSubject") || "").trim();
    extraSubjectInput.value = customSubject;
    if (customSubject) {
        setPlannerFeedback(`Extra subject enabled: ${customSubject}`, "success");
    } else {
        setPlannerFeedback("Using the default four subjects.", "neutral");
    }
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("studygraphTheme", theme);
    themeToggles.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.theme === theme);
    });
}

function initializeTheme() {
    const savedTheme = localStorage.getItem("studygraphTheme");
    if (savedTheme === "light" || savedTheme === "dark") {
        applyTheme(savedTheme);
        return;
    }

    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
}

function setStatus(target, message, tone = "neutral") {
    if (!target) {
        return;
    }
    target.textContent = message;
    target.className = `status ${tone}`;
}

function apiDateLabel(value) {
    return new Date(value).toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function renderSchedule(rows) {
    if (!scheduleBody) {
        return;
    }
    if (!rows || rows.length === 0) {
        scheduleBody.innerHTML = '<tr><td colspan="7" class="empty">No schedule loaded yet.</td></tr>';
        return;
    }

    scheduleBody.innerHTML = rows
        .map(
            (row) => `
                <tr>
                    <td>${row.sequence_no}</td>
                    <td>${row.title}</td>
                    <td>${row.scheduled_date}</td>
                    <td>${apiDateLabel(row.start_datetime)}</td>
                    <td>${apiDateLabel(row.end_datetime)}</td>
                    <td>
                        <div class="lesson-actions">
                            <button
                                class="button ghost schedule-action"
                                type="button"
                                data-schedule-id="${row.id}"
                                data-sequence-no="${row.sequence_no}"
                                data-title="${encodeURIComponent(row.title)}"
                                data-content="${encodeURIComponent(row.content || "")}"
                                data-context="${encodeURIComponent(row.learner_context || "")}"
                            >
                                ${row.content ? "Regenerate" : "Generate"}
                            </button>
                            ${row.content ? `
                                <button
                                    class="icon-button lesson-preview-button"
                                    type="button"
                                    title="Preview saved lesson"
                                    aria-label="Preview saved lesson for Day ${row.sequence_no}"
                                    data-preview-id="${row.id}"
                                    data-sequence-no="${row.sequence_no}"
                                    data-title="${encodeURIComponent(row.title)}"
                                    data-content="${encodeURIComponent(row.content || "")}"
                                >
                                    &#128065;
                                </button>
                            ` : ""}
                        </div>
                    </td>
                    <td>${row.calendar_event_id ? "Synced" : "Pending"}</td>
                </tr>
            `
        )
        .join("");

    document.querySelectorAll("[data-schedule-id]").forEach((button) => {
        button.addEventListener("click", () => {
            selectedScheduleId = Number(button.dataset.scheduleId);
            selectedScheduleTitle = decodeURIComponent(button.dataset.title);
            const sequenceNo = button.dataset.sequenceNo;
            const existingContent = decodeURIComponent(button.dataset.content || "");
            const existingContext = decodeURIComponent(button.dataset.context || "");

            if (selectedDayLabel) {
                selectedDayLabel.textContent = `Selected Day ${sequenceNo}: ${selectedScheduleTitle}`;
            }
            if (progressPromptInput) {
                progressPromptInput.value = existingContext;
            }
            if (lessonContent) {
                lessonContent.textContent = existingContent || "No lesson generated yet for this day.";
                lessonContent.classList.toggle("empty-state", !existingContent);
            }
            if (generateContentButton) {
                generateContentButton.disabled = false;
            }
        });
    });

    document.querySelectorAll("[data-preview-id]").forEach((button) => {
        button.addEventListener("click", () => {
            selectedScheduleId = null;
            selectedScheduleTitle = "";
            const sequenceNo = button.dataset.sequenceNo;
            const title = decodeURIComponent(button.dataset.title);
            const existingContent = decodeURIComponent(button.dataset.content || "");

            if (selectedDayLabel) {
                selectedDayLabel.textContent = `Previewing Day ${sequenceNo}: ${title}`;
            }
            if (progressPromptInput) {
                progressPromptInput.value = "";
            }
            if (lessonContent) {
                lessonContent.textContent = existingContent || "No lesson generated yet for this day.";
                lessonContent.classList.toggle("empty-state", !existingContent);
            }
            if (generateContentButton) {
                generateContentButton.disabled = true;
            }
        });
    });
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    const raw = await response.text();
    let data = null;

    try {
        data = raw ? JSON.parse(raw) : {};
    } catch (error) {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}. Check the Flask terminal for the full traceback.`);
        }
        throw new Error("Server returned a non-JSON response.");
    }

    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }
    return data;
}

function generateSchedule() {
    const subjects = getSubjects();
    const saved = localStorage.getItem("studySchedule");
    if (saved) {
        const parsed = JSON.parse(saved);
        return Array.from({ length: 7 }, (_, index) => {
            const row = parsed[index] || {};
            const normalized = {};
            const defaultHours = (2 / subjects.length).toFixed(2);
            subjects.forEach((subject) => {
                normalized[subject] = row[subject] ?? defaultHours;
            });
            return normalized;
        });
    }

    const defaultHours = (2 / subjects.length).toFixed(2);
    return Array.from({ length: 7 }, () => {
        const row = {};
        subjects.forEach((subject) => {
            row[subject] = defaultHours;
        });
        return row;
    });
}

function checkDayCompletion(day) {
    if (!rewardMessage) {
        return;
    }
    const subjects = getSubjects();
    const completion = JSON.parse(localStorage.getItem("taskCompletion") || "{}");
    const allDone = subjects.every((subject) => completion[`${day}-${subject}`]);

    if (allDone) {
        rewardMessage.textContent = `Completed all study targets for ${day}. Keep the streak going.`;
        rewardMessage.classList.remove("hidden");
        window.clearTimeout(window.rewardTimeout);
        window.rewardTimeout = window.setTimeout(() => {
            rewardMessage.classList.add("hidden");
        }, 3500);
    }
}

function renderCalendar(schedule) {
    if (!calendar) {
        return;
    }
    const subjects = getSubjects();
    const completion = JSON.parse(localStorage.getItem("taskCompletion") || "{}");
    calendar.innerHTML = "";

    days.forEach((day, dayIndex) => {
        const dayCard = document.createElement("article");
        dayCard.className = "day-card";

        const header = document.createElement("div");
        header.className = "day-card-top";

        const title = document.createElement("h3");
        title.textContent = day;

        const sticker = document.createElement("div");
        sticker.className = "sticker";
        sticker.textContent = emojis[dayIndex % emojis.length];

        const list = document.createElement("div");
        list.className = "subject-list";

        subjects.forEach((subject) => {
            const row = document.createElement("div");
            row.className = "subject-row";

            const label = document.createElement("label");
            label.textContent = subject;

            const input = document.createElement("input");
            input.type = "number";
            input.min = "0";
            input.step = "0.1";
            input.value = schedule[dayIndex][subject];
            input.addEventListener("change", () => {
                schedule[dayIndex][subject] = parseFloat(input.value || 0).toFixed(2);
            });

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            const key = `${day}-${subject}`;
            checkbox.checked = Boolean(completion[key]);
            checkbox.addEventListener("change", () => {
                completion[key] = checkbox.checked;
                localStorage.setItem("taskCompletion", JSON.stringify(completion));
                checkDayCompletion(day);
            });

            row.append(label, input, checkbox);
            list.appendChild(row);
        });

        const saveStatus = document.createElement("div");
        saveStatus.className = "day-save-status";
        saveStatus.textContent = "";

        const saveButton = document.createElement("button");
        saveButton.type = "button";
        saveButton.className = "button secondary save-hours-btn";
        saveButton.textContent = "Save Day Hours";
            saveButton.addEventListener("click", () => {
                localStorage.setItem("studySchedule", JSON.stringify(schedule));
                saveStatus.textContent = `Saved ${day} at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
                saveStatus.className = "day-save-status success";
                saveButton.textContent = "Saved";
                window.setTimeout(() => {
                    saveButton.textContent = "Save Day Hours";
                }, 1200);
                setStatus(feedback, `Saved custom study hours for ${day}.`, "success");
            });

        header.append(title, sticker);

        const saveMeta = document.createElement("div");
        saveMeta.className = "save-meta";
        saveMeta.append(saveStatus);

        dayCard.append(header, list, saveButton, saveMeta);
        calendar.appendChild(dayCard);
        checkDayCompletion(day);
    });
}

function displayRandomQuote() {
    if (!quoteElem) {
        return;
    }
    const index = Math.floor(Math.random() * quotes.length);
    quoteElem.textContent = quotes[index];
}

function loadTasks() {
    if (!taskList) {
        return;
    }
    const tasks = JSON.parse(localStorage.getItem("tasks") || "[]");
    taskList.innerHTML = "";
    tasks.forEach((task) => addTaskToList(task));
}

function persistTasks(tasks) {
    localStorage.setItem("tasks", JSON.stringify(tasks));
}

function addTaskToList(task) {
    if (!taskList) {
        return;
    }
    const item = document.createElement("li");
    const label = document.createElement("span");
    const remove = document.createElement("button");

    label.textContent = task;
    remove.type = "button";
    remove.className = "remove-btn";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
        const tasks = JSON.parse(localStorage.getItem("tasks") || "[]").filter((entry) => entry !== task);
        persistTasks(tasks);
        loadTasks();
    });

    item.append(label, remove);
    taskList.appendChild(item);
}

function updateTimerDisplay() {
    if (!timerDisplay) {
        return;
    }
    const hours = Math.floor(elapsedSeconds / 3600).toString().padStart(2, "0");
    const minutes = Math.floor((elapsedSeconds % 3600) / 60).toString().padStart(2, "0");
    const seconds = (elapsedSeconds % 60).toString().padStart(2, "0");
    timerDisplay.textContent = `${hours}:${minutes}:${seconds}`;
}

function loadTimerState() {
    elapsedSeconds = Number(localStorage.getItem("focusElapsedSeconds") || "0");
    updateTimerDisplay();
}

function resetLessonSelection() {
    if (!selectedDayLabel || !progressPromptInput || !lessonContent || !generateContentButton) {
        return;
    }
    selectedScheduleId = null;
    selectedScheduleTitle = "";
    selectedDayLabel.textContent = "Select a day from the schedule table first.";
    progressPromptInput.value = "";
    lessonContent.textContent = "No lesson generated yet.";
    lessonContent.classList.add("empty-state");
    generateContentButton.disabled = true;
}

function activateUtilityPanel(targetId) {
    if (!utilityTabs.length || !utilityPanels.length) {
        return;
    }
    utilityTabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab.dataset.utilityTarget === targetId);
    });
    utilityPanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.id === targetId);
    });
}

async function refreshSession() {
    try {
        const data = await apiRequest("/api/session", { method: "GET" });
        if (data.connected) {
            const label = data.email ? `Connected. Email saved: ${data.email}` : "Connected. Save your email below.";
            setStatus(authStatus, label, "success");
            if (data.email) {
                if (emailInput) {
                    emailInput.value = data.email;
                }
                setEmailFeedback(`Saved email: ${data.email}`, "success");
                await loadSchedule();
            }
        } else {
            setStatus(authStatus, "Not connected yet. Log in with Google first.", "neutral");
            setEmailFeedback("Email not saved in this session yet.", "neutral");
        }
    } catch (error) {
        setStatus(authStatus, error.message, "error");
        setEmailFeedback(error.message, "error");
    }
}

async function loadSchedule() {
    try {
        const data = await apiRequest("/api/schedule", { method: "GET" });
        renderSchedule(data.schedule);
    } catch (error) {
        renderSchedule([]);
        setStatus(feedback, error.message, "neutral");
    }
}

if (emailForm && emailInput && saveEmailButton) {
    emailForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setStatus(feedback, "Saving email...", "neutral");
        setEmailFeedback("Saving email...", "neutral");
        saveEmailButton.disabled = true;
        saveEmailButton.textContent = "Saving...";

        try {
            const data = await apiRequest("/api/session/email", {
                method: "POST",
                body: JSON.stringify({ email: emailInput.value })
            });
            setStatus(authStatus, `Connected. Email saved: ${data.email}`, "success");
            setStatus(feedback, data.message, "success");
            setEmailFeedback(`Saved email: ${data.email}`, "success");
            saveEmailButton.textContent = "Saved";
            await loadSchedule();
        } catch (error) {
            setStatus(feedback, error.message, "error");
            setEmailFeedback(error.message, "error");
            saveEmailButton.textContent = "Save Email";
        } finally {
            window.setTimeout(() => {
                saveEmailButton.disabled = false;
                saveEmailButton.textContent = "Save Email";
            }, 900);
        }
    });
}

function getPlannerPayload() {
    return {
        topic: topicInput?.value || "",
        duration_days: durationDaysInput?.value || "",
        focus_topic: focusTopicInput?.value || "",
        rest_days: restDaysInput?.value || "",
        study_time: studyTimeInput?.value || ""
    };
}

if (goalForm && topicInput && durationDaysInput) {
    goalForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setStatus(feedback, "Building your planner brief, generating the syllabus, and scheduling study dates...", "neutral");

        try {
            const data = await apiRequest("/api/generate-plan", {
                method: "POST",
                body: JSON.stringify(getPlannerPayload())
            });
            resetLessonSelection();
            renderSchedule(data.schedule);
            setStatus(feedback, data.message, "success");
        } catch (error) {
            setStatus(feedback, error.message, "error");
        }
    });
}

if (pushCalendarButton) {
    pushCalendarButton.addEventListener("click", async () => {
        setStatus(feedback, "Pushing unsynced events to Google Calendar...", "neutral");

        try {
            const data = await apiRequest("/api/push-calendar", {
                method: "POST",
                body: JSON.stringify({})
            });
            renderSchedule(data.schedule);
            setStatus(feedback, data.message, "success");
        } catch (error) {
            setStatus(feedback, error.message, "error");
        }
    });
}

if (contentForm && progressPromptInput) {
    contentForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!selectedScheduleId) {
            setStatus(feedback, "Select a day before generating lesson content.", "error");
            return;
        }

        setStatus(feedback, `Generating lesson content for ${selectedScheduleTitle}...`, "neutral");
        try {
            const data = await apiRequest("/api/generate-content", {
                method: "POST",
                body: JSON.stringify({
                    schedule_id: selectedScheduleId,
                    progress_prompt: progressPromptInput.value,
                    content_style: contentStyleInput?.value || "Detailed and practical"
                })
            });
            renderSchedule(data.schedule);
            if (data.item && lessonContent) {
                lessonContent.textContent = data.item.content || "No lesson generated yet.";
                lessonContent.classList.toggle("empty-state", !data.item.content);
            }
            setStatus(feedback, data.message, "success");
        } catch (error) {
            setStatus(feedback, error.message, "error");
        }
    });
}

if (newQuoteBtn) {
    newQuoteBtn.addEventListener("click", displayRandomQuote);
}

if (addTaskBtn && taskInput) {
    addTaskBtn.addEventListener("click", () => {
        const task = taskInput.value.trim();
        if (!task) {
            return;
        }

        const tasks = JSON.parse(localStorage.getItem("tasks") || "[]");
        tasks.push(task);
        persistTasks(tasks);
        taskInput.value = "";
        loadTasks();
    });
}

if (addSubjectButton && extraSubjectInput) {
    addSubjectButton.addEventListener("click", () => {
        const subject = extraSubjectInput.value.trim();
        if (!subject) {
            setPlannerFeedback("Type a subject name first.", "error");
            return;
        }
        if (defaultSubjects.some((item) => item.toLowerCase() === subject.toLowerCase())) {
            setPlannerFeedback("That subject already exists in the default planner.", "error");
            return;
        }

        localStorage.setItem("studygraphExtraSubject", subject);
        const updatedSchedule = generateSchedule();
        localStorage.setItem("studySchedule", JSON.stringify(updatedSchedule));
        syncSubjectControls();
        renderCalendar(updatedSchedule);
    });
}

if (clearSubjectButton) {
    clearSubjectButton.addEventListener("click", () => {
        localStorage.removeItem("studygraphExtraSubject");
        const updatedSchedule = generateSchedule();
        localStorage.setItem("studySchedule", JSON.stringify(updatedSchedule));
        syncSubjectControls();
        renderCalendar(updatedSchedule);
    });
}

if (startBtn && stopBtn && resetBtn) {
    startBtn.addEventListener("click", () => {
        if (timerInterval) {
            return;
        }

        timerInterval = window.setInterval(() => {
            elapsedSeconds += 1;
            localStorage.setItem("focusElapsedSeconds", String(elapsedSeconds));
            updateTimerDisplay();
        }, 1000);

        startBtn.disabled = true;
        stopBtn.disabled = false;
        resetBtn.disabled = false;
    });

    stopBtn.addEventListener("click", () => {
        window.clearInterval(timerInterval);
        timerInterval = null;
        startBtn.disabled = false;
        stopBtn.disabled = true;
    });

    resetBtn.addEventListener("click", () => {
        window.clearInterval(timerInterval);
        timerInterval = null;
        elapsedSeconds = 0;
        localStorage.setItem("focusElapsedSeconds", "0");
        updateTimerDisplay();
        startBtn.disabled = false;
        stopBtn.disabled = true;
        resetBtn.disabled = true;
    });
}

if (utilityTabs.length) {
    utilityTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            activateUtilityPanel(tab.dataset.utilityTarget);
        });
    });
    activateUtilityPanel("tasks-panel");
}

loadTasks();
loadTimerState();
renderCalendar(generateSchedule());
syncSubjectControls();
displayRandomQuote();
resetLessonSelection();
refreshSession();
initializeTheme();

themeToggles.forEach((button) => {
    button.addEventListener("click", () => {
        applyTheme(button.dataset.theme);
    });
});
