"""Fragmentos HTML reutilizables para formularios modales."""

from __future__ import annotations

from html import escape

ESTUDIANTE_FIELDS = (
    {
        "name": "codigo",
        "label": "Codigo del estudiante",
        "type": "text",
        "placeholder": "20240001",
    },
    {
        "name": "nombre",
        "label": "Nombre completo",
        "type": "text",
        "placeholder": "Ana Torres",
    },
)

NOTA_FIELDS = (
    {
        "name": "codigo",
        "label": "Codigo del estudiante",
        "type": "text",
        "placeholder": "20240001",
    },
    {
        "name": "materia",
        "label": "Materia",
        "type": "text",
        "placeholder": "Programacion",
    },
    {
        "name": "nota",
        "label": "Nota (0.0 a 10.0)",
        "type": "number",
        "step": "0.1",
        "placeholder": "8.5",
    },
)


def render_modal_form(
    modal_id: str,
    form_id: str,
    title: str,
    description: str,
    fields: tuple[dict[str, str], ...],
    submit_label: str,
) -> str:
    """Construye un dialogo HTML con un formulario estilizado."""
    bloques: list[str] = []
    for field in fields:
        step = f' step="{escape(field["step"])}"' if "step" in field else ""
        placeholder = (
            f' placeholder="{escape(field["placeholder"])}"'
            if "placeholder" in field
            else ""
        )
        bloques.append(
            """
            <label class="modal-field">
              <span>{label}</span>
              <input
                name="{name}"
                type="{type}"
                autocomplete="off"
                {step}{placeholder}
                required
              >
            </label>
            """.strip().format(
                label=escape(field["label"]),
                name=escape(field["name"]),
                type=escape(field["type"]),
                step=step,
                placeholder=placeholder,
            )
        )

    campos = "\n".join(bloques)
    return f"""
    <dialog id="{escape(modal_id)}" class="modal">
      <form id="{escape(form_id)}" class="modal-card" method="dialog">
        <button type="button" class="modal-close" data-close="{escape(modal_id)}">x</button>
        <p class="modal-kicker">Gestion academica</p>
        <h2 id="{escape(modal_id)}-title">{escape(title)}</h2>
        <p id="{escape(modal_id)}-description" class="modal-copy">{escape(description)}</p>
        <div class="modal-grid">
          {campos}
        </div>
        <div class="modal-actions">
          <button type="button" class="ghost-button" data-close="{escape(modal_id)}">
            Cancelar
          </button>
          <button id="{escape(modal_id)}-submit" type="submit" class="primary-button">
            {escape(submit_label)}
          </button>
        </div>
      </form>
    </dialog>
    """.strip()

