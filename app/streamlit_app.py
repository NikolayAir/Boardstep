import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="centered")

    st.title("Boardstep")
    st.caption("Chess practice in the browser.")

    st.write(
        "Boardstep is starting with a minimal Streamlit app. The first chess "
        "baseline will add board state, legal move validation, simple move input, "
        "move history, and tests."
    )

    st.subheader("Current milestone")
    st.write("Minimal app skeleton.")

    st.subheader("Planned local baseline")
    st.markdown(
        "- board state\n"
        "- legal move validation\n"
        "- simple move input\n"
        "- move history\n"
        "- tests"
    )

    st.subheader("Not included yet")
    st.markdown(
        "- online multiplayer\n"
        "- chess engine\n"
        "- AI or LLM-based chess coaching\n"
        "- user accounts\n"
        "- real-time backend"
    )


if __name__ == "__main__":
    main()
