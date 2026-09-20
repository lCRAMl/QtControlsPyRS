# prompt_editor.py
"""Eingabefeld für mehrteilige Prompts, mit hervorgehobenen Abschnitten.

Aus einer Liste von Abschnittsnamen ("Motiv", "Stil", ...) entstehen zwei
Dinge: ein Platzhaltertext, der die Abschnitte vorschlägt, und eine
Hervorhebung, die jede Zeile fett färbt, die mit einem Abschnittsnamen beginnt.
"""

from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PyQt6.QtWidgets import QTextEdit


class PromptHighlighter(QSyntaxHighlighter):
    """Hebt Zeilen hervor, die mit einem der Abschnittsnamen beginnen."""

    COLOR = "#8fd18f"

    def __init__(self, document: QTextDocument, sections: Iterable[str] = ()) -> None:
        super().__init__(document)
        self._sections: list[str] = list(sections)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._build_rules()

    def sections(self) -> list[str]:
        return list(self._sections)

    def setSections(self, sections: Iterable[str]) -> None:
        self._sections = list(sections)
        self._build_rules()
        self.rehighlight()

    def _build_rules(self) -> None:
        self._rules.clear()

        style = QTextCharFormat()
        style.setForeground(QColor(self.COLOR))
        style.setFontWeight(QFont.Weight.Bold)

        for section in self._sections:
            pattern = QRegularExpression(
                rf"^{QRegularExpression.escape(section)}\s*:?.*",
                QRegularExpression.PatternOption.MultilineOption,
            )
            self._rules.append((pattern, style))

    def highlightBlock(self, text: str) -> None:
        for pattern, style in self._rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), style)


class PromptEditor(QTextEdit):
    """QTextEdit, das seine Abschnitte kennt und hervorhebt."""

    def __init__(self, sections: Iterable[str] = (), parent=None) -> None:
        super().__init__(parent)
        self._highlighter = PromptHighlighter(self.document())
        self.setSections(sections)

    def sections(self) -> list[str]:
        return self._highlighter.sections()

    def setSections(self, sections: Iterable[str]) -> None:
        """Übernimmt neue Abschnitte — auch während das Feld schon gefüllt ist."""
        names = list(sections)
        self.setPlaceholderText("\n".join(f"{name}:" for name in names))
        self._highlighter.setSections(names)

    def highlighter(self) -> PromptHighlighter:
        return self._highlighter
