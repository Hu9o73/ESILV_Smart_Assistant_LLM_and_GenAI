import reflex as rx

from .state import State


def password_gate() -> rx.Component:
    return rx.box(
        rx.box(
            rx.text("Accès", class_name="modal-kicker"),
            rx.text("Entrez le mot de passe", class_name="modal-title"),
            rx.text(
                "Le même mot de passe que celui attendu par le backend `/message`.",
                class_name="modal-body",
            ),
            rx.input(
                value=State.password_input,
                on_change=State.set_password_input,
                placeholder="Mot de passe",
                type_="password",
                class_name="modal-input",
            ),
            rx.cond(
                State.password_error,
                rx.text(State.password_error, class_name="modal-error"),
                rx.fragment(),
            ),
            rx.button(
                "Valider",
                on_click=State.validate_password,
                class_name="modal-button",
            ),
            class_name="modal-card",
        ),
        class_name="modal-overlay",
    )


def message_bubble(message) -> rx.Component:
    return rx.box(
        rx.box(
            rx.markdown(message.content, class_name="chat-markdown"),
            rx.cond(
                (message.role == "assistant") & (message.meta != None),
                rx.box(
                    rx.cond(
                        message.meta.status == "fallback",
                        rx.text(
                            message.meta.fallback_label,
                            class_name="meta-warning",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        (message.meta.status == "approved") & (message.meta.attempts > 1),
                        rx.text(
                            message.meta.attempts_label,
                            class_name="meta-text",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        message.meta.reformulated_query,
                        rx.text(
                            message.meta.reformulated_label,
                            class_name="meta-muted",
                        ),
                        rx.fragment(),
                    ),
                    class_name="meta-block",
                ),
                rx.fragment(),
            ),
            rx.text(message.time_label, class_name="message-timestamp"),
            class_name=rx.cond(message.role == "user", "bubble-user", "bubble-assistant"),
        ),
        class_name=rx.cond(message.role == "user", "message-row end", "message-row start"),
    )


def index() -> rx.Component:
    return rx.box(
        rx.cond(State.is_authenticated, rx.fragment(), password_gate()),
        rx.box(
            rx.box(
                rx.box(
                    rx.image(src="/logo.png", alt="Chat'akon", class_name="brand-logo"),
                    rx.box(
                        rx.text("Chat'akon", class_name="brand-title"),
                        rx.text(
                            "Pose tes questions sur la vie étudiante, les cours ou les services du Pôle.",
                            class_name="brand-subtitle",
                        ),
                        class_name="brand-copy",
                    ),
                    class_name="brand",
                ),
                rx.button(
                    rx.text("↺", class_name="reset-icon"),
                    rx.text("Nouvelle discussion"),
                    on_click=State.reset_conversation,
                    class_name="reset-button",
                ),
                class_name="header-inner",
            ),
            class_name="header",
        ),
        rx.box(
            rx.box(
                rx.box(
                    rx.text("Assistant étudiant", class_name="section-kicker"),
                    rx.text("Bonjour !", class_name="section-title"),
                    rx.text(
                        "Laisse un message pour obtenir de l'aide sur les emplois du temps, "
                        "la vie associative ou les services du campus à La Défense.",
                        class_name="section-body",
                    ),
                    rx.box(
                        rx.foreach(
                            State.suggestion_chips,
                            lambda chip: rx.button(
                                "✦ " + chip,
                                on_click=State.apply_suggestion(chip),
                                class_name="chip",
                            ),
                        ),
                        class_name="chip-row",
                    ),
                    class_name="intro-left",
                ),
                rx.box(
                    rx.text("Comment ça marche ?", class_name="how-title"),
                    rx.text(
                        "• Les messages sont mis en file, puis traités par le backend agentique.\n"
                        "• Les réponses sont validées par un agent de vérification.\n"
                        "• Les métadonnées de validation sont affichées si besoin.",
                        class_name="how-body",
                    ),
                    class_name="how-box",
                ),
                class_name="intro-card",
            ),
            rx.box(
                rx.box(
                    rx.text("Fil de discussion", class_name="thread-kicker"),
                    rx.text(
                        "L'assistant garde le contexte tant que la session reste ouverte.",
                        class_name="thread-subtitle",
                    ),
                    class_name="thread-header",
                ),
                rx.box(
                    rx.foreach(State.conversation, message_bubble),
                    rx.cond(
                        State.is_loading,
                        rx.box(
                            rx.spinner(color="var(--sky-500)", size="2"),
                            rx.text(State.job_status_label, class_name="loading-text"),
                            class_name="loading-row",
                        ),
                        rx.fragment(),
                    ),
                    class_name="thread-body",
                ),
                rx.box(
                    rx.text_area(
                        value=State.new_message,
                        on_change=State.set_new_message,
                        placeholder=(
                            "Ex: Quels sont les horaires du Learning Center cette semaine ?"
                        ),
                        class_name="message-input",
                    ),
                    rx.box(
                        rx.cond(
                            State.error_message,
                            rx.text(State.error_message, class_name="error-text"),
                            rx.text(
                                "Astuce : Entrée pour envoyer, Shift + Entrée pour une nouvelle ligne.",
                                class_name="hint-text",
                            ),
                        ),
                        rx.button(
                            rx.cond(
                                State.is_loading,
                                rx.box(
                                    rx.spinner(size="1"),
                                    rx.text("Envoi"),
                                    class_name="send-loading",
                                ),
                                rx.text("Envoyer"),
                            ),
                            on_click=State.send_message,
                            is_disabled=State.is_loading | (State.new_message == ""),
                            class_name="send-button",
                        ),
                        class_name="composer-row",
                    ),
                    class_name="composer",
                ),
                class_name="thread-card",
            ),
            class_name="main",
        ),
        class_name="page",
    )


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap",
        "/styles.css",
    ]
)
app.add_page(index, title="Chat'akon")
