/**
 * Render the board into the Streamlit component root and report square clicks
 * back to Python.
 */
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    const root = parentElement.querySelector("#boardstep-clickable-board");

    const files = data?.files || ["a", "b", "c", "d", "e", "f", "g", "h"];
    const disabled = Boolean(data?.disabled);
    // Map outline white-piece glyphs to filled glyphs so CSS color styling is consistent.
    const whiteToFilledSymbol = {
        "♔": "♚",
        "♕": "♛",
        "♖": "♜",
        "♗": "♝",
        "♘": "♞",
        "♙": "♟"
    };
    const blackSymbols = new Set(["♚", "♛", "♜", "♝", "♞", "♟"]);

    function makeLabel(text, className) {
        const label = document.createElement("div");
        label.className = className;
        label.textContent = text;
        return label;
    }

    function makeSquare(row, fileName, rowIndex, fileIndex) {
        const squareName = `${fileName}${row.rank}`;
        const button = document.createElement("button");
        const isLight = (rowIndex + fileIndex) % 2 === 0;

        button.type = "button";
        button.className = `boardstep-square ${isLight ? "boardstep-light" : "boardstep-dark"}`;
        button.setAttribute("aria-label", `Select ${squareName}`);
        button.dataset.square = squareName;
        button.disabled = disabled;
        button.setAttribute("aria-disabled", String(disabled));

        if (disabled) {
            button.classList.add("boardstep-disabled");
        }

        if (data?.selectedSquare === squareName) {
            button.classList.add("boardstep-selected");
        }

        if ((data?.legalTargets || []).includes(squareName)) {
            button.classList.add("boardstep-legal-target");
        }

        const rawPiece = row[fileName] || "";
        const piece = whiteToFilledSymbol[rawPiece] || rawPiece;

        if (piece) {
            const pieceSpan = document.createElement("span");
            // Keep chess glyphs in text presentation, not emoji presentation.
            pieceSpan.textContent = piece + "\ufe0e";

            if (whiteToFilledSymbol[rawPiece]) {
                pieceSpan.className = "boardstep-piece-white";
            } else if (blackSymbols.has(rawPiece)) {
                pieceSpan.className = "boardstep-piece-black";
            }

            button.appendChild(pieceSpan);
        }

        button.onclick = () => {
            if (!disabled) {
                setTriggerValue("square", squareName);
            }
        };

        return button;
    }

    root.replaceChildren();

    (data?.rows || []).forEach((row, rowIndex) => {
        root.appendChild(makeLabel(row.rank, "boardstep-rank-label"));

        files.forEach((fileName, fileIndex) => {
            root.appendChild(makeSquare(row, fileName, rowIndex, fileIndex));
        });
    });

    root.appendChild(makeLabel("", "boardstep-file-label"));

    files.forEach((fileName) => {
        root.appendChild(makeLabel(fileName, "boardstep-file-label"));
    });
}
