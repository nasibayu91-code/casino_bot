# games/mines.py
"""Логика игры Mines"""

import random
from typing import List, Tuple


class MinesGame:
    """Игра Mines - открывай ячейки, избегая мин"""
    
    def __init__(self, mines_count: int = 3, grid_size: int = 5):
        self.mines_count = mines_count
        self.grid_size = grid_size
        self.total_cells = grid_size * grid_size
        self.board = self._generate_board()
        self.opened_cells = 0
        self.is_game_over = False
        self.current_multiplier = 1.0
    
    def _generate_board(self) -> List[str]:
        """Генерация игрового поля"""
        board = ['💎'] * (self.total_cells - self.mines_count)
        board.extend(['💣'] * self.mines_count)
        random.shuffle(board)
        return board
    
    def open_cell(self, position: int) -> dict:
        """Открыть ячейку"""
        if position < 0 or position >= self.total_cells:
            return {"error": "Неверная позиция"}
        
        if self.is_game_over:
            return {"error": "Игра окончена"}
        
        cell = self.board[position]
        
        if cell == '💣':
            self.is_game_over = True
            return {
                "won": False,
                "multiplier": 0,
                "cell": cell,
                "position": position,
                "opened": self.opened_cells
            }
        
        # Открыта безопасная ячейка
        self.opened_cells += 1
        self.board[position] = '✅'  # Помечаем как открытую
        
        # Рассчитываем новый множитель
        safe_cells_left = self.total_cells - self.mines_count - self.opened_cells
        if safe_cells_left > 0:
            self.current_multiplier = round(1 + (self.opened_cells * 0.3), 2)
        
        return {
            "won": True,
            "multiplier": self.current_multiplier,
            "cell": cell,
            "position": position,
            "opened": self.opened_cells,
            "can_continue": True
        }
    
    def cash_out(self, bet: int) -> dict:
        """Забрать выигрыш"""
        if self.is_game_over:
            return {"won": False, "profit": -bet}
        
        profit = int(bet * self.current_multiplier)
        return {
            "won": True,
            "multiplier": self.current_multiplier,
            "profit": profit,
            "opened": self.opened_cells
        }
    
    def get_board_display(self) -> str:
        """Получить отображение поля"""
        display = ""
        for i in range(0, self.total_cells, self.grid_size):
            row = self.board[i:i+self.grid_size]
            display += " ".join(row) + "\n"
        return display