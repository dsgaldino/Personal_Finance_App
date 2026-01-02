from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.app_config import BRAND


CSS_PATH = Path("app/assets/styles.css")


def apply_global_css() -> None:
    if not CSS_PATH.exists():
        return
    css = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def inject_sidebar_nav_header() -> None:
    """
    Inject a header above Streamlit's st.navigation sidebar menu.
    """
    title = f"{BRAND.icon_emoji} {BRAND.name}"
    subtitle = BRAND.subtitle

    st.markdown(
        f"""
        <script>
          (function() {{
            const tryInject = () => {{
              const nav = parent.document.querySelector('[data-testid="stSidebarNav"]');
              if (!nav) return false;

              if (nav.querySelector('.galdiex-nav-header')) return true;

              const header = parent.document.createElement('div');
              header.className = 'galdiex-nav-header';
              header.innerHTML = `
                <div class="galdiex-nav-title">{title}</div>
                <div class="galdiex-nav-subtitle">{subtitle}</div>
              `;

              nav.prepend(header);
              return true;
            }};

            const interval = setInterval(() => {{
              if (tryInject()) clearInterval(interval);
            }}, 50);
          }})();
        </script>
        """,
        unsafe_allow_html=True,
    )
