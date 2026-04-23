const state = {
  currentStudent: null,
  selectedCode: null,
  selectedMatter: null,
  studentMode: "create",
  gradeMode: "create",
  students: [],
  filters: {
    query: "",
    status: "todos",
  },
};

const elements = {
  summaryTotal: document.getElementById("summary-total"),
  summaryAverage: document.getElementById("summary-average"),
  summaryApproved: document.getElementById("summary-approved"),
  summaryFailed: document.getElementById("summary-failed"),
  summarySubjects: document.getElementById("summary-subjects"),
  studentsBody: document.getElementById("students-body"),
  notesBody: document.getElementById("notes-body"),
  detailName: document.getElementById("detail-name"),
  detailCode: document.getElementById("detail-code"),
  detailAverage: document.getElementById("detail-average"),
  detailStatus: document.getElementById("detail-status"),
  statusText: document.getElementById("status-text"),
  statusIndicator: document.getElementById("status-indicator"),
  databaseLabel: document.getElementById("database-label"),
  reportsDir: document.getElementById("reports-dir"),
  search: document.getElementById("student-search"),
  statusFilter: document.getElementById("status-filter"),
  resultsCounter: document.getElementById("results-counter"),
  studentsMeta: document.getElementById("students-meta"),
  studentModal: document.getElementById("student-modal"),
  gradeModal: document.getElementById("grade-modal"),
  studentForm: document.getElementById("student-form"),
  gradeForm: document.getElementById("grade-form"),
  editStudentButton: document.getElementById("edit-student-button"),
  deleteStudentButton: document.getElementById("delete-student-button"),
  editNoteButton: document.getElementById("edit-note-button"),
  deleteNoteButton: document.getElementById("delete-note-button"),
};

const studentInputs = {
  codigo: elements.studentForm.querySelector('input[name="codigo"]'),
  nombre: elements.studentForm.querySelector('input[name="nombre"]'),
};

const gradeInputs = {
  codigo: elements.gradeForm.querySelector('input[name="codigo"]'),
  materia: elements.gradeForm.querySelector('input[name="materia"]'),
  nota: elements.gradeForm.querySelector('input[name="nota"]'),
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new Error(data.error || "Ocurrio un error inesperado.");
  }

  return data;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(message, tone = "info") {
  elements.statusText.textContent = message;
  elements.statusIndicator.className = `indicator ${tone}`;
}

function setDisabled(element, disabled) {
  element.disabled = disabled;
  element.classList.toggle("is-disabled", disabled);
}

function syncActionState() {
  const hasStudent = Boolean(state.selectedCode);
  const hasMatter = Boolean(state.selectedMatter);

  setDisabled(elements.editStudentButton, !hasStudent);
  setDisabled(elements.deleteStudentButton, !hasStudent);
  setDisabled(elements.editNoteButton, !(hasStudent && hasMatter));
  setDisabled(elements.deleteNoteButton, !(hasStudent && hasMatter));
}

function renderSummary(summary) {
  elements.summaryTotal.textContent = summary.estudiantes_totales;
  elements.summaryAverage.textContent = Number(summary.promedio_general).toFixed(2);
  elements.summaryApproved.textContent = summary.aprobados;
  elements.summaryFailed.textContent = summary.reprobados;
  elements.summarySubjects.textContent = summary.materias_totales;
  elements.studentsMeta.textContent = `Sin notas: ${summary.sin_notas}`;
}

function getFilteredStudents() {
  return state.students.filter((student) => {
    const query = state.filters.query.trim().toLowerCase();
    const matchesQuery =
      !query ||
      student.nombre.toLowerCase().includes(query) ||
      student.codigo.toLowerCase().includes(query);
    const matchesStatus =
      state.filters.status === "todos" || student.estado === state.filters.status;
    return matchesQuery && matchesStatus;
  });
}

function renderStudents() {
  const students = getFilteredStudents();
  elements.resultsCounter.textContent = `${students.length} resultado(s)`;

  if (students.length === 0) {
    const message = state.students.length
      ? "No hay coincidencias con el filtro actual."
      : "Todavia no hay estudiantes cargados.";
    elements.studentsBody.innerHTML = `
      <tr>
        <td colspan="5" class="empty-state">${message}</td>
      </tr>
    `;
    return;
  }

  elements.studentsBody.innerHTML = students
    .map((student) => {
      const activeClass = student.codigo === state.selectedCode ? "active" : "";
      return `
        <tr class="${activeClass}" data-code="${escapeHtml(student.codigo)}">
          <td>${escapeHtml(student.codigo)}</td>
          <td>${escapeHtml(student.nombre)}</td>
          <td>${student.materias_totales}</td>
          <td>${Number(student.promedio).toFixed(2)}</td>
          <td>${escapeHtml(student.estado)}</td>
        </tr>
      `;
    })
    .join("");

  elements.studentsBody.querySelectorAll("tr[data-code]").forEach((row) => {
    row.addEventListener("click", () => {
      selectStudent(row.dataset.code);
    });
  });
}

function clearDetail() {
  state.currentStudent = null;
  state.selectedCode = null;
  state.selectedMatter = null;
  elements.detailName.textContent = "Sin seleccion";
  elements.detailCode.textContent = "Sin seleccion";
  elements.detailAverage.textContent = "0.00";
  elements.detailStatus.textContent = "Pendiente";
  elements.detailStatus.className = "status-pill neutral";
  elements.notesBody.innerHTML = `
    <tr>
      <td colspan="2" class="empty-state">
        Selecciona un estudiante para ver sus notas.
      </td>
    </tr>
  `;
  syncActionState();
}

function renderNotes(student, preferredMatter = null) {
  const entries = Object.entries(student.notas || {}).sort(([a], [b]) => a.localeCompare(b));
  const preferredSelection = entries.find(([matter]) => matter === preferredMatter)?.[0] || null;
  const existingSelection = entries.find(([matter]) => matter === state.selectedMatter)?.[0];
  state.selectedMatter = preferredSelection || existingSelection || null;

  if (entries.length === 0) {
    state.selectedMatter = null;
    elements.notesBody.innerHTML = `
      <tr>
        <td colspan="2" class="empty-state">El estudiante no tiene notas registradas.</td>
      </tr>
    `;
    syncActionState();
    return;
  }

  elements.notesBody.innerHTML = entries
    .map(([matter, note]) => {
      const activeClass = state.selectedMatter === matter ? "active" : "";
      return `
        <tr class="${activeClass}" data-matter="${escapeHtml(matter)}">
          <td>${escapeHtml(matter)}</td>
          <td>${Number(note).toFixed(2)}</td>
        </tr>
      `;
    })
    .join("");

  elements.notesBody.querySelectorAll("tr[data-matter]").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedMatter = row.dataset.matter;
      renderNotes(student);
      syncActionState();
    });
  });

  syncActionState();
}

function renderDetail(student, preferredMatter = null) {
  state.currentStudent = student;
  state.selectedCode = student.codigo;
  elements.detailName.textContent = student.nombre;
  elements.detailCode.textContent = student.codigo;
  elements.detailAverage.textContent = Number(student.promedio).toFixed(2);
  elements.detailStatus.textContent = student.estado;
  elements.detailStatus.className = `status-pill ${student.estado.toLowerCase()}`;
  renderNotes(student, preferredMatter);
  renderStudents();
}

async function selectStudent(code, preferredMatter = null) {
  try {
    const student = await request(`/api/students/${encodeURIComponent(code)}`);
    renderDetail(student, preferredMatter);
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function loadMeta() {
  try {
    const meta = await request("/api/meta");
    elements.databaseLabel.textContent = meta.database;
    elements.reportsDir.textContent = meta.reports_dir;
  } catch {
    elements.databaseLabel.textContent = "PostgreSQL";
    elements.reportsDir.textContent = "storage/reportes";
  }
}

async function loadDashboard(preferredCode = null, preferredMatter = null) {
  try {
    const [summary, students] = await Promise.all([
      request("/api/summary"),
      request("/api/students"),
    ]);

    state.students = students;
    renderSummary(summary);
    renderStudents();

    const filteredStudents = getFilteredStudents();
    const codeToLoad =
      preferredCode || state.selectedCode || filteredStudents[0]?.codigo || state.students[0]?.codigo || null;

    if (codeToLoad) {
      await selectStudent(codeToLoad, preferredMatter);
    } else {
      clearDetail();
    }
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function openDialog(dialog) {
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  }
}

function closeDialog(dialog) {
  if (dialog.open) {
    dialog.close();
  }
}

function configureModal(dialog, { title, description, submitLabel }) {
  dialog.querySelector("h2").textContent = title;
  dialog.querySelector(".modal-copy").textContent = description;
  dialog.querySelector(".primary-button").textContent = submitLabel;
}

function prepareStudentModal(mode) {
  state.studentMode = mode;
  elements.studentForm.reset();

  if (mode === "create") {
    configureModal(elements.studentModal, {
      title: "Nuevo estudiante",
      description: "Crea un estudiante con codigo unico y nombre obligatorio.",
      submitLabel: "Guardar estudiante",
    });
    studentInputs.codigo.readOnly = false;
    studentInputs.codigo.value = "";
    studentInputs.nombre.value = "";
  } else {
    if (!state.currentStudent) {
      setStatus("Selecciona un estudiante antes de intentar editarlo.", "warning");
      return;
    }
    configureModal(elements.studentModal, {
      title: "Editar estudiante",
      description: "El codigo se conserva como identificador fijo para mantener integridad.",
      submitLabel: "Guardar cambios",
    });
    studentInputs.codigo.readOnly = true;
    studentInputs.codigo.value = state.currentStudent.codigo;
    studentInputs.nombre.value = state.currentStudent.nombre;
  }

  openDialog(elements.studentModal);
}

function prepareGradeModal(mode) {
  state.gradeMode = mode;
  elements.gradeForm.reset();

  if (mode === "create") {
    configureModal(elements.gradeModal, {
      title: "Registrar nota",
      description: "Agrega una nueva materia para el estudiante seleccionado o manualmente por codigo.",
      submitLabel: "Guardar nota",
    });
    gradeInputs.codigo.readOnly = Boolean(state.selectedCode);
    gradeInputs.codigo.value = state.selectedCode || "";
    gradeInputs.materia.value = "";
    gradeInputs.nota.value = "";
  } else {
    if (!state.currentStudent || !state.selectedMatter) {
      setStatus("Selecciona una materia antes de editar la nota.", "warning");
      return;
    }
    configureModal(elements.gradeModal, {
      title: "Editar nota",
      description: "Puedes cambiar el nombre de la materia y ajustar la calificacion.",
      submitLabel: "Guardar cambios",
    });
    gradeInputs.codigo.readOnly = true;
    gradeInputs.codigo.value = state.currentStudent.codigo;
    gradeInputs.materia.value = state.selectedMatter;
    gradeInputs.nota.value = state.currentStudent.notas[state.selectedMatter];
  }

  openDialog(elements.gradeModal);
}

async function handleStudentSubmit(event) {
  event.preventDefault();
  try {
    const payload = Object.fromEntries(new FormData(elements.studentForm).entries());
    const student =
      state.studentMode === "create"
        ? await request("/api/students", {
            method: "POST",
            body: JSON.stringify(payload),
          })
        : await request(`/api/students/${encodeURIComponent(payload.codigo)}`, {
            method: "PUT",
            body: JSON.stringify({ nombre: payload.nombre }),
          });

    closeDialog(elements.studentModal);
    await loadDashboard(student.codigo, state.selectedMatter);
    setStatus(
      state.studentMode === "create"
        ? `Estudiante ${student.nombre} registrado correctamente.`
        : `Estudiante ${student.nombre} actualizado correctamente.`,
      "success"
    );
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleGradeSubmit(event) {
  event.preventDefault();
  try {
    const payload = Object.fromEntries(new FormData(elements.gradeForm).entries());
    const student =
      state.gradeMode === "create"
        ? await request("/api/grades", {
            method: "POST",
            body: JSON.stringify(payload),
          })
        : await request(
            `/api/grades/${encodeURIComponent(payload.codigo)}/${encodeURIComponent(state.selectedMatter)}`,
            {
              method: "PUT",
              body: JSON.stringify({
                materia: payload.materia,
                nota: payload.nota,
              }),
            }
          );

    closeDialog(elements.gradeModal);
    await loadDashboard(student.codigo, payload.materia);
    setStatus(
      state.gradeMode === "create"
        ? `Nota registrada para ${student.nombre} en ${payload.materia}.`
        : `Nota actualizada para ${student.nombre}.`,
      "success"
    );
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleDeleteStudent() {
  if (!state.selectedCode || !state.currentStudent) {
    setStatus("Selecciona un estudiante antes de eliminarlo.", "warning");
    return;
  }

  const confirmed = window.confirm(
    `Se eliminara el estudiante ${state.currentStudent.nombre} (${state.currentStudent.codigo}).`
  );
  if (!confirmed) {
    return;
  }

  try {
    const result = await request(`/api/students/${encodeURIComponent(state.selectedCode)}`, {
      method: "DELETE",
    });
    state.selectedCode = null;
    state.selectedMatter = null;
    await loadDashboard();
    setStatus(`Estudiante ${result.nombre} eliminado correctamente.`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleDeleteNote() {
  if (!state.selectedCode || !state.selectedMatter) {
    setStatus("Selecciona una materia antes de eliminarla.", "warning");
    return;
  }

  const confirmed = window.confirm(
    `Se eliminara la materia ${state.selectedMatter} del estudiante ${state.selectedCode}.`
  );
  if (!confirmed) {
    return;
  }

  try {
    const result = await request(
      `/api/grades/${encodeURIComponent(state.selectedCode)}/${encodeURIComponent(state.selectedMatter)}`,
      { method: "DELETE" }
    );
    const codigo = result.resumen.codigo;
    state.selectedMatter = null;
    await loadDashboard(codigo);
    setStatus(`Materia eliminada del estudiante ${codigo}.`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleStudentReport() {
  if (!state.selectedCode) {
    setStatus("Selecciona un estudiante antes de generar su reporte.", "warning");
    return;
  }

  try {
    const result = await request(`/api/reports/${encodeURIComponent(state.selectedCode)}`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setStatus(`Reporte individual generado en ${result.ruta}.`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleAllReports() {
  try {
    const result = await request("/api/reports", {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (!result.rutas.length) {
      setStatus("No hay estudiantes registrados para generar reportes.", "warning");
      return;
    }
    setStatus(`Se generaron ${result.rutas.length} reporte(s) en ${elements.reportsDir.textContent}.`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function bindFilters() {
  elements.search.addEventListener("input", (event) => {
    state.filters.query = event.target.value;
    renderStudents();
  });
  elements.statusFilter.addEventListener("change", (event) => {
    state.filters.status = event.target.value;
    renderStudents();
  });
}

function bindEvents() {
  document.getElementById("refresh-button").addEventListener("click", () => loadDashboard());
  document.getElementById("new-student-button").addEventListener("click", () => {
    prepareStudentModal("create");
  });
  document.getElementById("new-grade-button").addEventListener("click", () => {
    prepareGradeModal("create");
  });
  document.getElementById("student-report-button").addEventListener("click", handleStudentReport);
  document.getElementById("all-reports-button").addEventListener("click", handleAllReports);
  elements.editStudentButton.addEventListener("click", () => prepareStudentModal("edit"));
  elements.deleteStudentButton.addEventListener("click", handleDeleteStudent);
  elements.editNoteButton.addEventListener("click", () => prepareGradeModal("edit"));
  elements.deleteNoteButton.addEventListener("click", handleDeleteNote);
  elements.studentForm.addEventListener("submit", handleStudentSubmit);
  elements.gradeForm.addEventListener("submit", handleGradeSubmit);

  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.close);
      closeDialog(target);
    });
  });

  bindFilters();
}

bindEvents();
loadMeta();
loadDashboard();
