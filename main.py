#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
黑白棋（Reversi / Othello）完整实现
=====================================
功能：
  1. ReversiGame 核心逻辑类（8x8 棋盘，8方向翻转检测）
  2. AIPlayer 类：minimax / alpha-beta剪枝 / MCTS 三种算法
  3. tkinter GUI：左右布局、实时计时、日志输出、多线程AI计算
  4. Benchmark 性能对比
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import math
import random
import copy


# ============================================================
# 第一部分：核心游戏逻辑
# ============================================================

class ReversiGame:
    """
    黑白棋核心逻辑类
    棋盘用 8x8 二维列表表示：
        0  = 空位
        1  = 黑棋
       -1  = 白棋
    黑棋先手。
    """

    # 八个方向偏移量：上下左右 + 四个对角线
    DIRECTIONS = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    def __init__(self):
        """初始化 8x8 棋盘，并在中央放置 4 颗初始棋子"""
        self.board_size = 8
        self.board = [[0] * self.board_size for _ in range(self.board_size)]
        # 中央四格：白黑 / 黑白
        mid = self.board_size // 2
        self.board[mid - 1][mid - 1] = 1   # 黑
        self.board[mid - 1][mid] = -1       # 白
        self.board[mid][mid - 1] = -1       # 白
        self.board[mid][mid] = 1            # 黑
        # 当前轮到谁走：1=黑，-1=白
        self.current_player = 1
        # 记录历史（用于悔棋），每条记录为 (board_snapshot, player)
        self.history = []

    def get_current_player(self):
        """返回当前玩家（1=黑，-1=白）"""
        return self.current_player

    def get_board_copy(self):
        """返回棋盘的深拷贝"""
        return copy.deepcopy(self.board)

    def set_board(self, board_snapshot, player):
        """从快照恢复棋盘和当前玩家"""
        self.board = copy.deepcopy(board_snapshot)
        self.current_player = player

    def _in_bounds(self, r, c):
        """检查坐标 (r, c) 是否在棋盘范围内"""
        return 0 <= r < self.board_size and 0 <= c < self.board_size

    def is_valid_move(self, row, col, player=None):
        """
        判断 (row, col) 是否为当前玩家（或指定 player）的合法落子。
        合法条件：
          1. 该位置为空
          2. 至少存在一个方向能翻转对方棋子
        """
        if player is None:
            player = self.current_player
        # 位置必须为空
        if self.board[row][col] != 0:
            return False
        # 检查八个方向是否能翻转
        for dr, dc in self.DIRECTIONS:
            if self._can_flip_direction(row, col, dr, dc, player):
                return True
        return False

    def _can_flip_direction(self, row, col, dr, dc, player):
        """
        检查从 (row, col) 沿 (dr, dc) 方向是否能翻转对方棋子。
        条件：紧邻位置为对方棋子，沿该方向连续为对方棋子，最终以己方棋子结尾。
        """
        opponent = -player
        r, c = row + dr, col + dc
        # 紧邻必须是对方棋子
        if not self._in_bounds(r, c) or self.board[r][c] != opponent:
            return False
        # 沿方向继续查找
        while self._in_bounds(r, c) and self.board[r][c] == opponent:
            r += dr
            c += dc
        # 最终以己方棋子结尾才算合法
        return self._in_bounds(r, c) and self.board[r][c] == player

    def flip_pieces(self, row, col, player=None):
        """
        在 (row, col) 落子并翻转所有被夹住的对方棋子。
        落子成功返回 True，否则返回 False。
        """
        if player is None:
            player = self.current_player
        if not self.is_valid_move(row, col, player):
            return False
        # 保存历史（用于悔棋）
        self.history.append((self.get_board_copy(), self.current_player))
        # 放置棋子
        self.board[row][col] = player
        # 八个方向翻转
        for dr, dc in self.DIRECTIONS:
            self._flip_direction(row, col, dr, dc, player)
        # 切换当前玩家
        self.current_player = -player
        return True

    def _flip_direction(self, row, col, dr, dc, player):
        """沿 (dr, dc) 方向翻转所有被夹住的对方棋子"""
        opponent = -player
        to_flip = []
        r, c = row + dr, col + dc
        # 收集需要翻转的棋子
        while self._in_bounds(r, c) and self.board[r][c] == opponent:
            to_flip.append((r, c))
            r += dr
            c += dc
        # 如果末端是己方棋子，则执行翻转
        if self._in_bounds(r, c) and self.board[r][c] == player:
            for fr, fc in to_flip:
                self.board[fr][fc] = player

    def get_valid_moves(self, player=None):
        """
        返回当前玩家（或指定 player）的所有合法落子位置列表。
        每个元素为 (row, col) 元组。
        """
        if player is None:
            player = self.current_player
        moves = []
        for r in range(self.board_size):
            for c in range(self.board_size):
                if self.is_valid_move(r, c, player):
                    moves.append((r, c))
        return moves

    def is_game_over(self):
        """
        判断游戏是否结束。
        游戏结束条件：双方都没有合法落子。
        """
        # 如果当前玩家有合法落子，游戏未结束
        if self.get_valid_moves(self.current_player):
            return False
        # 如果对手也没有合法落子，游戏结束
        if self.get_valid_moves(-self.current_player):
            return False
        return True

    def get_score(self):
        """统计黑白双方棋子数，返回 (黑棋数, 白棋数)"""
        black = sum(cell == 1 for row in self.board for cell in row)
        white = sum(cell == -1 for row in self.board for cell in row)
        return black, white

    def undo(self):
        """
        悔棋：恢复到上一步的状态。
        成功返回 True，无法悔棋返回 False。
        """
        if not self.history:
            return False
        board_snapshot, player = self.history.pop()
        self.set_board(board_snapshot, player)
        return True


# ============================================================
# 第二部分：AI 玩家
# ============================================================

class AIPlayer:
    """
    AI 玩家类，包含三种搜索算法：
      1. minimax        —— 基础极大极小搜索
      2. alpha_beta     —— Alpha-Beta 剪枝优化
      3. mcts           —— 蒙特卡洛树搜索（基于时间限制）
    共用评估函数：位置权重矩阵 + 行动力
    所有算法内置 55 秒超时保护。
    """

    # ---- 位置权重矩阵 ----
    # 角位最高（100），X位（对角相邻角）最低（-25），
    # C位（边相邻角）较低（-12），中心区域中等。
    WEIGHT_MATRIX = [
        [100, -20,  10,   5,   5,  10, -20, 100],
        [-20, -50,  -2,  -2,  -2,  -2, -50, -20],
        [ 10,  -2,   8,   1,   1,   8,  -2,  10],
        [  5,  -2,   1,   0,   0,   1,  -2,   5],
        [  5,  -2,   1,   0,   0,   1,  -2,   5],
        [ 10,  -2,   8,   1,   1,   8,  -2,  10],
        [-20, -50,  -2,  -2,  -2,  -2, -50, -20],
        [100, -20,  10,   5,   5,  10, -20, 100],
    ]

    # 超时阈值（秒）
    TIMEOUT = 55

    def __init__(self, color):
        """
        初始化 AI 玩家。
        color: 1=黑棋，-1=白棋
        """
        self.color = color

    # ---- 评估函数 ----

    def evaluate(self, game, player):
        """
        评估当前棋盘对 player 的有利程度。
        综合两个维度：
          1. 位置权重分：每个棋子按权重矩阵加分
          2. 行动力：合法落子数越多越好
        返回值越大表示对 player 越有利。
        """
        # 位置权重分
        pos_score = 0
        for r in range(8):
            for c in range(8):
                if game.board[r][c] == player:
                    pos_score += self.WEIGHT_MATRIX[r][c]
                elif game.board[r][c] == -player:
                    pos_score -= self.WEIGHT_MATRIX[r][c]

        # 行动力（合法落子数差异）
        my_moves = len(game.get_valid_moves(player))
        opp_moves = len(game.get_valid_moves(-player))
        # 如果一方无子可下，给予极大奖励/惩罚
        if my_moves == 0 and opp_moves == 0:
            # 游戏结束，按棋子数判定
            black, white = game.get_score()
            my_count = black if player == 1 else white
            opp_count = white if player == 1 else black
            if my_count > opp_count:
                return 10000
            elif my_count < opp_count:
                return -10000
            else:
                return 0
        if my_moves == 0:
            return -5000  # 无子可下非常不利
        if opp_moves == 0:
            return 5000   # 对手无子可下非常有利

        mobility_score = 10 * (my_moves - opp_moves)

        # 棋子数差异（终局阶段权重更高）
        total_pieces = sum(abs(game.board[r][c]) for r in range(8) for c in range(8))
        if total_pieces > 50:
            # 终局阶段，棋子数更重要
            black, white = game.get_score()
            my_count = black if player == 1 else white
            opp_count = white if player == 1 else black
            piece_score = 5 * (my_count - opp_count)
        else:
            piece_score = 0

        return pos_score + mobility_score + piece_score

    # ---- 超时检查辅助 ----

    def _check_timeout(self, start_time):
        """检查是否超时（55秒），超时则抛出 TimeoutError"""
        if time.time() - start_time > self.TIMEOUT:
            raise TimeoutError("AI 思考超时，强制返回当前最优解")

    # ---- 算法 1：Minimax ----

    def minimax(self, game, depth):
        """
        基础 Minimax 算法（无剪枝）。
        参数：
            game  : ReversiGame 实例
            depth : 搜索深度
        返回：
            (best_move, node_count, elapsed_ms)
            best_move  : 最佳落子 (row, col)，无合法落子则为 None
            node_count : 搜索的节点总数
            elapsed_ms : 耗时（毫秒）
        """
        start_time = time.time()
        node_count = [0]  # 用列表以便在嵌套函数中修改
        best_move = [None]
        best_score = [-float('inf')]

        try:
            moves = game.get_valid_moves(self.color)
            if not moves:
                return None, 0, 0.0

            for move in moves:
                self._check_timeout(start_time)
                # 模拟落子
                sim = copy.deepcopy(game)
                sim.flip_pieces(move[0], move[1], self.color)
                # 递归搜索
                score = self._minimax_recursive(sim, depth - 1, False, start_time, node_count)
                if score > best_score[0]:
                    best_score[0] = score
                    best_move[0] = move

        except TimeoutError:
            pass  # 超时，返回当前已找到的最优解

        elapsed_ms = (time.time() - start_time) * 1000
        return best_move[0], node_count[0], elapsed_ms

    def _minimax_recursive(self, game, depth, is_maximizing, start_time, node_count):
        """Minimax 递归辅助函数"""
        node_count[0] += 1
        self._check_timeout(start_time)

        # 终止条件：深度为0 或 游戏结束
        if depth == 0 or game.is_game_over():
            return self.evaluate(game, self.color)

        current_player = game.get_current_player()
        moves = game.get_valid_moves(current_player)

        # 如果当前玩家无合法落子，跳过
        if not moves:
            game.current_player = -current_player
            result = self._minimax_recursive(game, depth - 1, not is_maximizing, start_time, node_count)
            game.current_player = current_player
            return result

        if is_maximizing:
            max_eval = -float('inf')
            for move in moves:
                sim = copy.deepcopy(game)
                sim.flip_pieces(move[0], move[1], current_player)
                eval_score = self._minimax_recursive(sim, depth - 1, False, start_time, node_count)
                max_eval = max(max_eval, eval_score)
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                sim = copy.deepcopy(game)
                sim.flip_pieces(move[0], move[1], current_player)
                eval_score = self._minimax_recursive(sim, depth - 1, True, start_time, node_count)
                min_eval = min(min_eval, eval_score)
            return min_eval

    # ---- 算法 2：Alpha-Beta 剪枝 ----

    def alpha_beta(self, game, depth):
        """
        Alpha-Beta 剪枝算法。
        参数：
            game  : ReversiGame 实例
            depth : 搜索深度
        返回：
            (best_move, node_count, elapsed_ms)
        """
        start_time = time.time()
        node_count = [0]
        best_move = [None]
        best_score = [-float('inf')]

        try:
            moves = game.get_valid_moves(self.color)
            if not moves:
                return None, 0, 0.0

            alpha = -float('inf')
            beta = float('inf')

            for move in moves:
                self._check_timeout(start_time)
                sim = copy.deepcopy(game)
                sim.flip_pieces(move[0], move[1], self.color)
                score = self._alpha_beta_recursive(sim, depth - 1, alpha, beta, False, start_time, node_count)
                if score > best_score[0]:
                    best_score[0] = score
                    best_move[0] = move
                alpha = max(alpha, score)

        except TimeoutError:
            pass

        elapsed_ms = (time.time() - start_time) * 1000
        return best_move[0], node_count[0], elapsed_ms

    def _alpha_beta_recursive(self, game, depth, alpha, beta, is_maximizing, start_time, node_count):
        """Alpha-Beta 递归辅助函数"""
        node_count[0] += 1
        self._check_timeout(start_time)

        if depth == 0 or game.is_game_over():
            return self.evaluate(game, self.color)

        current_player = game.get_current_player()
        moves = game.get_valid_moves(current_player)

        if not moves:
            game.current_player = -current_player
            result = self._alpha_beta_recursive(game, depth - 1, alpha, beta, not is_maximizing, start_time, node_count)
            game.current_player = current_player
            return result

        if is_maximizing:
            max_eval = -float('inf')
            for move in moves:
                sim = copy.deepcopy(game)
                sim.flip_pieces(move[0], move[1], current_player)
                eval_score = self._alpha_beta_recursive(sim, depth - 1, alpha, beta, False, start_time, node_count)
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Beta 剪枝
            return max_eval
        else:
            min_eval = float('inf')
            for move in moves:
                sim = copy.deepcopy(game)
                sim.flip_pieces(move[0], move[1], current_player)
                eval_score = self._alpha_beta_recursive(sim, depth - 1, alpha, beta, True, start_time, node_count)
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha 剪枝
            return min_eval

    # ---- 算法 3：蒙特卡洛树搜索（MCTS） ----

    def mcts(self, game, time_limit=5.0, max_simulations=5000):
        """
        蒙特卡洛树搜索（MCTS）。
        基于时间限制，在限定时间内尽可能多地模拟。
        参数：
            game          : ReversiGame 实例
            time_limit    : 时间限制（秒），默认5秒
            max_simulations: 最大模拟次数，默认5000
        返回：
            (best_move, simulation_count, elapsed_ms)
        """
        start_time = time.time()
        # 实际超时上限，取 time_limit 和 TIMEOUT 的较小值
        effective_limit = min(time_limit, self.TIMEOUT)

        moves = game.get_valid_moves(self.color)
        if not moves:
            return None, 0, 0.0

        # 初始化每个落子位置的统计信息：[总胜利次数, 模拟次数]
        stats = {move: [0.0, 0] for move in moves}
        simulation_count = 0

        try:
            while simulation_count < max_simulations:
                self._check_timeout(start_time)
                if time.time() - start_time > effective_limit:
                    break

                # 随机选择一个落子位置进行模拟
                move = random.choice(moves)
                result = self._mcts_simulate(game, move)
                stats[move][0] += result
                stats[move][1] += 1
                simulation_count += 1

        except TimeoutError:
            pass

        # 选择平均得分最高的落子
        best_move = None
        best_avg = -float('inf')
        for move in moves:
            if stats[move][1] > 0:
                avg = stats[move][0] / stats[move][1]
                if avg > best_avg:
                    best_avg = avg
                    best_move = move

        elapsed_ms = (time.time() - start_time) * 1000
        return best_move, simulation_count, elapsed_ms

    def _mcts_simulate(self, game, first_move):
        """
        从 first_move 开始模拟一局随机对弈。
        返回：1（AI赢）、-1（AI输）、0（平局）
        """
        sim = copy.deepcopy(game)
        sim.flip_pieces(first_move[0], first_move[1], self.color)

        # 模拟随机对弈直到游戏结束
        max_steps = 64  # 最多64步
        steps = 0
        while not sim.is_game_over() and steps < max_steps:
            steps += 1
            current = sim.get_current_player()
            moves = sim.get_valid_moves(current)
            if not moves:
                # 当前玩家无子可下，切换
                sim.current_player = -current
                continue
            # 随机选择一步
            move = random.choice(moves)
            sim.flip_pieces(move[0], move[1], current)

        # 统计结果
        black, white = sim.get_score()
        if self.color == 1:
            if black > white:
                return 1
            elif black < white:
                return -1
            else:
                return 0
        else:
            if white > black:
                return 1
            elif white < black:
                return -1
            else:
                return 0


# ============================================================
# 第三部分：GUI 界面
# ============================================================

class ReversiGUI:
    """
    黑白棋 GUI 界面，基于 tkinter。
    左右布局：
      左侧  —— Canvas 绘制棋盘和棋子
      右侧  —— 控制面板（算法选择、参数输入、按钮、计时器、日志）
    """

    # 棋盘绘制参数
    CELL_SIZE = 60          # 每格像素
    MARGIN = 30             # 棋盘边距
    BOARD_COLOR = "#228B22" # 棋盘绿色
    LINE_COLOR = "#000000"  # 线条颜色
    BLACK_COLOR = "#111111" # 黑棋颜色
    WHITE_COLOR = "#F5F5F5" # 白棋颜色
    HINT_COLOR = "#FFD700"  # 合法落子提示颜色

    def __init__(self, root):
        """初始化 GUI"""
        self.root = root
        self.root.title("黑白棋 Reversi")
        self.root.resizable(False, False)

        # 游戏核心对象
        self.game = ReversiGame()
        # AI 对象（初始为白棋）
        self.ai = AIPlayer(-1)
        # 玩家颜色（黑棋先手）
        self.player_color = 1
        # AI 是否在思考中
        self.ai_thinking = False
        # 计时相关
        self.game_start_time = time.time()
        self.player_step_start = None
        self.ai_step_start = None
        # 游戏是否结束
        self.game_over = False
        # 是否正在对局中（用于锁定 AI 设置）
        self.game_in_progress = False
        # 是否处于设置阶段（点了"开始新游戏"但还没"确认设置"）
        self.setup_phase = False

        # 构建界面
        self._build_ui()
        # 绘制棋盘
        self._draw_board()
        # 显示合法落子提示
        self._show_hints()
        # 启动计时器心跳
        self._update_timer()
        # 启动 60 秒超时检测
        self._start_timeout_watchdog()
        # 记录玩家开始计时
        self.player_step_start = None

        # ---- 初始状态：AI 设置可编辑，等待玩家点击"开始新游戏" ----
        self._set_ai_settings_locked(False)

        # ---- 强制窗口显示并置顶 ----
        self.root.deiconify()                  # 取消隐藏（如果有隐藏操作）
        self.root.attributes('-topmost', True) # 强制窗口置顶，不被控制台挡住
        self.root.lift()                       # 把窗口拽到最前面
        self.root.focus_force()                # 强制抢夺焦点

        # ---- 窗口居中显示 ----
        self.root.update_idletasks()           # 先刷新一次，确保尺寸已计算
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"+{x}+{y}")        # 设置窗口位置为屏幕正中央

    # ---- 界面构建 ----

    def _build_ui(self):
        """构建左右布局的界面"""
        # 主框架：左右排列
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- 左侧：棋盘画布 ----
        canvas_size = self.CELL_SIZE * 8 + self.MARGIN * 2
        self.canvas = tk.Canvas(
            main_frame, width=canvas_size, height=canvas_size,
            bg=self.BOARD_COLOR, highlightthickness=0
        )
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
        # 绑定鼠标点击事件
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # ---- 右侧：控制面板 ----
        control_frame = tk.Frame(main_frame, width=320, padx=10, pady=10)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        control_frame.pack_propagate(False)

        # 标题
        tk.Label(control_frame, text="黑白棋 Reversi", font=("Microsoft YaHei", 16, "bold")).pack(pady=(0, 10))

        # ---- 算法选择 ----
        algo_frame = tk.LabelFrame(control_frame, text="AI 设置", padx=5, pady=5)
        algo_frame.pack(fill=tk.X, pady=5)

        tk.Label(algo_frame, text="算法：").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.algo_var = tk.StringVar(value="alpha_beta")
        self.algo_combo = ttk.Combobox(
            algo_frame, textvariable=self.algo_var,
            values=["minimax", "alpha_beta", "mcts"],
            state="readonly", width=15
        )
        self.algo_combo.grid(row=0, column=1, pady=2)

        tk.Label(algo_frame, text="深度/时间：").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.depth_var = tk.StringVar(value="4")
        self.depth_entry = tk.Entry(algo_frame, textvariable=self.depth_var, width=18)
        self.depth_entry.grid(row=1, column=1, pady=2)
        tk.Label(algo_frame, text="(minimax/AB用深度, MCTS用秒)", font=("Microsoft YaHei", 8)).grid(
            row=2, column=0, columnspan=2, sticky=tk.W
        )

        # ---- 按钮区域 ----
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        # "开始新游戏"按钮
        self.btn_new = tk.Button(btn_frame, text="开始新游戏", command=self._new_game, width=14)
        self.btn_new.pack(side=tk.LEFT, padx=5)

        # "确认设置并开始"按钮（初始禁用，点击"开始新游戏"后才可用）
        self.btn_confirm = tk.Button(
            btn_frame, text="确认设置", command=self._confirm_settings,
            width=14, state="disabled"
        )
        self.btn_confirm.pack(side=tk.LEFT, padx=5)

        # ---- 第二行按钮：悔棋 + 认输 ----
        btn_frame2 = tk.Frame(control_frame)
        btn_frame2.pack(fill=tk.X, pady=5)

        self.btn_undo = tk.Button(btn_frame2, text="悔棋", command=self._undo, width=14)
        self.btn_undo.pack(side=tk.LEFT, padx=5)

        self.btn_surrender = tk.Button(
            btn_frame2, text="认输结束", command=self._surrender,
            width=14, state="disabled"
        )
        self.btn_surrender.pack(side=tk.LEFT, padx=5)

        # ---- 计时器区域 ----
        timer_frame = tk.LabelFrame(control_frame, text="计时", padx=5, pady=5)
        timer_frame.pack(fill=tk.X, pady=5)

        self.lbl_player_time = tk.Label(timer_frame, text="玩家本步耗时: 0.00 秒", anchor=tk.W)
        self.lbl_player_time.pack(fill=tk.X, pady=1)
        self.lbl_ai_time = tk.Label(timer_frame, text="AI 本步耗时: 0.00 秒", anchor=tk.W)
        self.lbl_ai_time.pack(fill=tk.X, pady=1)
        self.lbl_total_time = tk.Label(timer_frame, text="游戏总耗时: 0.00 秒", anchor=tk.W)
        self.lbl_total_time.pack(fill=tk.X, pady=1)

        # ---- 当前状态 ----
        self.lbl_status = tk.Label(
            control_frame, text="当前：黑棋（你）", font=("Microsoft YaHei", 12, "bold"),
            fg="#111111"
        )
        self.lbl_status.pack(pady=5)

        # ---- 日志区域 ----
        tk.Label(control_frame, text="游戏日志", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(
            control_frame, height=12, width=38,
            font=("Consolas", 9), state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

    # ---- 日志输出 ----

    def _log(self, message):
        """向日志区追加一条消息（线程安全，使用 after 在主线程执行）"""
        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _append)

    # ---- 棋盘绘制 ----

    def _draw_board(self):
        """在 Canvas 上绘制棋盘网格和所有棋子"""
        self.canvas.delete("all")
        m = self.MARGIN
        cs = self.CELL_SIZE

        # 绘制网格线
        for i in range(9):
            # 横线
            self.canvas.create_line(m, m + i * cs, m + 8 * cs, m + i * cs, fill=self.LINE_COLOR)
            # 竖线
            self.canvas.create_line(m + i * cs, m, m + i * cs, m + 8 * cs, fill=self.LINE_COLOR)

        # 绘制星位（天元和四个角星）
        star_points = [(3, 3), (3, 5), (5, 3), (5, 5)]
        for sr, sc in star_points:
            x = m + sc * cs + cs // 2
            y = m + sr * cs + cs // 2
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=self.LINE_COLOR)

        # 绘制棋子
        for r in range(8):
            for c in range(8):
                if self.game.board[r][c] != 0:
                    self._draw_piece(r, c, self.game.board[r][c])

    def _draw_piece(self, row, col, color):
        """在 (row, col) 位置绘制一颗棋子"""
        m = self.MARGIN
        cs = self.CELL_SIZE
        cx = m + col * cs + cs // 2
        cy = m + row * cs + cs // 2
        radius = cs // 2 - 5
        fill = self.BLACK_COLOR if color == 1 else self.WHITE_COLOR
        outline = "#333333" if color == 1 else "#999999"
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=fill, outline=outline, width=2
        )

    def _show_hints(self):
        """在合法落子位置显示半透明提示圆点"""
        self.canvas.delete("hint")
        if self.game_over or self.ai_thinking:
            return
        current = self.game.get_current_player()
        if current != self.player_color:
            return
        moves = self.game.get_valid_moves(self.player_color)
        m = self.MARGIN
        cs = self.CELL_SIZE
        for r, c in moves:
            cx = m + c * cs + cs // 2
            cy = m + r * cs + cs // 2
            self.canvas.create_oval(
                cx - 8, cy - 8, cx + 8, cy + 8,
                fill=self.HINT_COLOR, outline="", tags="hint"
            )

    # ---- 鼠标点击处理 ----

    def _on_canvas_click(self, event):
        """处理棋盘点击事件：玩家落子"""
        if self.game_over or self.ai_thinking:
            return
        # 判断是否轮到玩家
        if self.game.get_current_player() != self.player_color:
            return
        # 将像素坐标转换为棋盘坐标
        m = self.MARGIN
        cs = self.CELL_SIZE
        col = (event.x - m) // cs
        row = (event.y - m) // cs
        # 边界检查
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        # 尝试落子
        if self.game.is_valid_move(row, col, self.player_color):
            self.game.flip_pieces(row, col, self.player_color)
            self._log(f"玩家落子于 ({row}, {col})")
            # 计算玩家本步耗时
            if self.player_step_start:
                step_time = time.time() - self.player_step_start
                self._log(f"玩家思考耗时 {step_time:.2f} 秒")
            self.player_step_start = None
            # 刷新界面
            self._draw_board()
            self._show_hints()
            self._update_status()
            # 检查游戏是否结束
            if self.game.is_game_over():
                self._end_game()
                return
            # 切换到 AI 回合
            self._start_ai_turn()
        else:
            self._log(f"({row}, {col}) 不是合法落子位置")

    # ---- AI 回合 ----

    def _start_ai_turn(self):
        """启动 AI 思考（在子线程中执行，避免阻塞主界面）"""
        self.ai_thinking = True
        self.ai_step_start = time.time()
        self._show_hints()  # 清除提示
        self._update_status()
        self._log(f"AI 开始思考（{self.algo_var.get()}）...")

        def ai_worker():
            """AI 计算子线程"""
            try:
                algo = self.algo_var.get()
                if algo == "minimax":
                    depth = int(self.depth_var.get())
                    move, nodes, elapsed = self.ai.minimax(self.game, depth)
                    self.root.after(0, lambda: self._on_ai_complete(move, nodes, elapsed))
                elif algo == "alpha_beta":
                    depth = int(self.depth_var.get())
                    move, nodes, elapsed = self.ai.alpha_beta(self.game, depth)
                    self.root.after(0, lambda: self._on_ai_complete(move, nodes, elapsed))
                elif algo == "mcts":
                    time_limit = float(self.depth_var.get())
                    move, sims, elapsed = self.ai.mcts(self.game, time_limit=time_limit)
                    self.root.after(0, lambda: self._on_ai_complete(moves=move, nodes=sims, elapsed=elapsed))
            except Exception as e:
                self.root.after(0, lambda: self._on_ai_error(str(e)))

        thread = threading.Thread(target=ai_worker, daemon=True)
        thread.start()

    def _on_ai_complete(self, moves, nodes, elapsed):
        """AI 计算完成回调（在主线程中执行）"""
        self.ai_thinking = False
        if moves is None:
            self._log("AI 无合法落子，跳过回合")
            self.game.current_player = -self.game.current_player
            self.player_step_start = time.time()
            self._show_hints()
            self._update_status()
            if self.game.is_game_over():
                self._end_game()
            return

        row, col = moves
        self.game.flip_pieces(row, col, self.ai.color)
        self._log(f"AI 落子于 ({row}, {col})")
        self._log(f"AI 思考耗时 {elapsed:.1f} ms，搜索 {nodes} 个节点")

        self._draw_board()
        self.player_step_start = time.time()
        self.ai_step_start = None
        self._show_hints()
        self._update_status()

        if self.game.is_game_over():
            self._end_game()

    def _on_ai_error(self, error_msg):
        """AI 计算出错回调"""
        self.ai_thinking = False
        self._log(f"AI 出错: {error_msg}")
        messagebox.showerror("AI 错误", f"AI 计算出错:\n{error_msg}")
        self.player_step_start = time.time()
        self._show_hints()
        self._update_status()

    # ---- 状态更新 ----

    def _update_status(self):
        """更新状态标签"""
        current = self.game.get_current_player()
        black, white = self.game.get_score()
        if current == self.player_color:
            self.lbl_status.config(text=f"当前：黑棋（你）  黑{black}:白{white}", fg="#111111")
        else:
            self.lbl_status.config(text=f"当前：白棋（AI）  黑{black}:白{white}", fg="#666666")

    def _update_timer(self):
        """每 100ms 刷新一次计时器显示（使用 root.after）"""
        # 玩家本步耗时
        if self.player_step_start and not self.game_over:
            pt = time.time() - self.player_step_start
            self.lbl_player_time.config(text=f"玩家本步耗时: {pt:.2f} 秒")
        # AI 本步耗时
        if self.ai_step_start and not self.game_over:
            at = time.time() - self.ai_step_start
            self.lbl_ai_time.config(text=f"AI 本步耗时: {at:.2f} 秒")
        # 游戏总耗时
        total = time.time() - self.game_start_time
        self.lbl_total_time.config(text=f"游戏总耗时: {total:.2f} 秒")
        # 持续心跳
        self.root.after(100, self._update_timer)

    def _start_timeout_watchdog(self):
        """
        60 秒心跳检测：如果玩家单步超过 60 秒，弹窗判负。
        每 1 秒检查一次。
        """
        if self.game_over:
            return
        if self.player_step_start:
            elapsed = time.time() - self.player_step_start
            if elapsed > 60:
                self._log("玩家超时（60秒），判负！")
                messagebox.showwarning("超时", "玩家思考超时 60 秒，AI 获胜！")
                self.game_over = True
                return
        self.root.after(1000, self._start_timeout_watchdog)

    # ---- 游戏结束 ----

    def _end_game(self):
        """游戏结束处理（正常结束：棋盘已满或双方无子可下）"""
        self.game_over = True
        self.game_in_progress = False
        self.setup_phase = False
        # 解锁 AI 设置，允许下一局重新配置
        self._set_ai_settings_locked(False)
        # "开始新游戏"恢复可用
        self.btn_new.config(state="normal")
        # "认输结束"按钮禁用
        self.btn_surrender.config(state="disabled")
        # "确认设置"按钮禁用
        self.btn_confirm.config(state="disabled")
        black, white = self.game.get_score()
        if black > white:
            result = f"黑棋胜！ {black}:{white}"
            winner = "黑棋（你）" if self.player_color == 1 else "AI"
        elif white > black:
            result = f"白棋胜！ {black}:{white}"
            winner = "白棋（你）" if self.player_color == -1 else "AI"
        else:
            result = f"平局！ {black}:{white}"
            winner = "平局"
        self._log(f"游戏结束 —— {result}")
        self._log("AI 设置已解锁，可修改后开始新游戏")
        self.lbl_status.config(text=f"游戏结束: {result}")
        messagebox.showinfo("游戏结束", f"{result}\n{winner} 获胜！")

    def _end_game_by_timeout(self):
        """超时判负结束：解锁设置并弹窗"""
        self.game_over = True
        self.game_in_progress = False
        self.setup_phase = False
        self._set_ai_settings_locked(False)
        # "开始新游戏"恢复可用
        self.btn_new.config(state="normal")
        # "认输结束"按钮禁用
        self.btn_surrender.config(state="disabled")
        # "确认设置"按钮禁用
        self.btn_confirm.config(state="disabled")
        self._log("玩家超时，AI 设置已解锁")
        self.lbl_status.config(text="游戏结束: 玩家超时判负")
        messagebox.showwarning("超时", "玩家思考超时 60 秒，AI 获胜！")

    def _surrender(self):
        """玩家主动认输结束游戏"""
        if not self.game_in_progress:
            return
        # 二次确认，防止误点
        confirm = messagebox.askyesno("认输", "确定要认输结束本局吗？")
        if not confirm:
            return
        self.game_over = True
        self.game_in_progress = False
        self._set_ai_settings_locked(False)
        self.btn_surrender.config(state="disabled")
        black, white = self.game.get_score()
        result = f"玩家认输！ 黑{black}:白{white}"
        self._log(f"玩家主动认输 —— {result}")
        self._log("AI 设置已解锁，可修改后开始新游戏")
        self.lbl_status.config(text=f"游戏结束: {result}")
        messagebox.showinfo("认输", f"{result}\nAI 获胜！")

    # ---- 按钮回调 ----

    def _set_ai_settings_locked(self, locked):
        """
        锁定或解锁 AI 设置控件。
        游戏进行中 locked=True，设置阶段 locked=False。
        """
        if locked:
            # 锁定：禁用下拉框和输入框，防止中途修改
            self.algo_combo.config(state="disabled")
            self.depth_entry.config(state="disabled")
        else:
            # 解锁：恢复可选状态
            self.algo_combo.config(state="readonly")
            self.depth_entry.config(state="normal")

    def _new_game(self):
        """
        开始新游戏（进入设置阶段）。
        重置棋盘，解锁 AI 设置让玩家配置，等玩家点"确认设置"后才正式开局。
        """
        self.game = ReversiGame()
        self.ai = AIPlayer(-1)
        self.game_over = False
        self.game_in_progress = False
        self.setup_phase = True
        self.ai_thinking = False
        self.player_step_start = None
        self.ai_step_start = None
        # 解锁 AI 设置，让玩家自由配置
        self._set_ai_settings_locked(False)
        # "确认设置"按钮启用
        self.btn_confirm.config(state="normal")
        # "开始新游戏"按钮禁用（防止重复点击）
        self.btn_new.config(state="disabled")
        # "认输结束"按钮禁用
        self.btn_surrender.config(state="disabled")
        self._draw_board()
        self._show_hints()
        self._update_status()
        self._log("===== 请配置 AI 设置，然后点击「确认设置」开始对局 =====")
        self.lbl_status.config(text="设置阶段：请配置AI后点「确认设置」", fg="#CC6600")

    def _confirm_settings(self):
        """
        确认 AI 设置，锁定配置并正式开始对局计时。
        """
        if not self.setup_phase:
            return
        self.setup_phase = False
        self.game_in_progress = True
        # 锁定 AI 设置，本局不可再改
        self._set_ai_settings_locked(True)
        # "确认设置"按钮禁用
        self.btn_confirm.config(state="disabled")
        # "认输结束"按钮启用
        self.btn_surrender.config(state="normal")
        # 正式开始计时
        self.game_start_time = time.time()
        self.player_step_start = time.time()
        self.ai_step_start = None
        algo = self.algo_var.get()
        depth = self.depth_var.get()
        self._log(f"===== 设置已确认并锁定 =====")
        self._log(f"算法={algo}，深度/时间={depth}，对局开始！")
        self._update_status()

    def _surrender(self):
        """玩家主动认输结束游戏"""
        if not self.game_in_progress:
            return
        # 二次确认，防止误点
        confirm = messagebox.askyesno("认输", "确定要认输结束本局吗？")
        if not confirm:
            return
        self.game_over = True
        self.game_in_progress = False
        self._set_ai_settings_locked(False)
        # "开始新游戏"恢复可用
        self.btn_new.config(state="normal")
        # "认输结束"按钮禁用
        self.btn_surrender.config(state="disabled")
        black, white = self.game.get_score()
        result = f"玩家认输！ 黑{black}:白{white}"
        self._log(f"玩家主动认输 —— {result}")
        self._log("AI 设置已解锁，可修改后开始新游戏")
        self.lbl_status.config(text=f"游戏结束: {result}")
        messagebox.showinfo("认输", f"{result}\nAI 获胜！")

    def _undo(self):
        """悔棋：撤回玩家和AI各一步"""
        if self.ai_thinking:
            self._log("AI 正在思考，无法悔棋")
            return
        if self.game_over:
            self.game_over = False
        # 撤回两步（AI一步 + 玩家一步）
        if self.game.undo():
            self.game.undo()
            self._log("悔棋成功（撤回两步）")
            self._draw_board()
            self._show_hints()
            self._update_status()
            self.player_step_start = time.time()
        else:
            self._log("无法悔棋（没有历史记录）")

    def _surrender(self):
        """认输结束"""
        if self.game_over:
            return
        self.game_over = True
        self._log("玩家认输，游戏结束！")
        self._log("AI 设置已解锁，可修改后开始新游戏")
        self.lbl_status.config(text="游戏结束: 玩家认输")
        messagebox.showinfo("游戏结束", "玩家认输，AI 获胜！")


# ============================================================
# 第四部分：Benchmark 性能测试
# ============================================================

def run_benchmark():
    """
    运行 Benchmark 性能对比测试。
    自动输出 Markdown 格式的性能对比表格，
    包含各种算法在不同深度和模拟次数下的节点数和耗时。
    """
    print("=" * 60)
    print("  黑白棋 AI Benchmark 性能测试")
    print("=" * 60)

    # 定义测试用的棋盘局面（从初始局面开始）
    game = ReversiGame()

    # 模拟几步以得到一个更复杂的局面
    test_moves = [(2, 3), (2, 2), (3, 2), (4, 2), (4, 1)]
    for r, c in test_moves:
        if game.is_valid_move(r, c):
            game.flip_pieces(r, c)

    print(f"\n当前局面：黑{game.get_score()[0]} 白{game.get_score()[1]}")
    print(f"合法落子数：{len(game.get_valid_moves())}")
    print()

    # ---- 测试配置 ----
    # minimax 和 alpha_beta 测试不同深度
    depths = [1, 2, 3, 4, 5]
    # MCTS 测试不同模拟次数
    mcts_times = [0.5, 1.0, 2.0, 5.0]

    ai_black = AIPlayer(1)   # 黑棋 AI
    ai_white = AIPlayer(-1)  # 白棋 AI

    # ---- Markdown 表头 ----
    md_lines = []
    md_lines.append("# 黑白棋 AI 性能对比报告\n")
    md_lines.append(f"**测试局面**: 黑{game.get_score()[0]} 白{game.get_score()[1]}，"
                    f"合法落子 {len(game.get_valid_moves())} 个\n")
    md_lines.append(f"**Python 版本**: 3.x | **系统**: Windows\n")

    # ---- Minimax 测试 ----
    md_lines.append("## 1. Minimax 算法\n")
    md_lines.append("| 深度 | 最佳落子 | 搜索节点数 | 耗时 (ms) |")
    md_lines.append("|------|----------|-----------|----------|")

    for depth in depths:
        print(f"  测试 minimax depth={depth} ...")
        move, nodes, elapsed = ai_black.minimax(game, depth)
        move_str = f"({move[0]},{move[1]})" if move else "None"
        md_lines.append(f"| {depth} | {move_str} | {nodes} | {elapsed:.1f} |")
        print(f"    -> 落子 {move_str}, 节点 {nodes}, 耗时 {elapsed:.1f} ms")

    md_lines.append("")

    # ---- Alpha-Beta 测试 ----
    md_lines.append("## 2. Alpha-Beta 剪枝算法\n")
    md_lines.append("| 深度 | 最佳落子 | 搜索节点数 | 耗时 (ms) |")
    md_lines.append("|------|----------|-----------|----------|")

    for depth in depths:
        print(f"  测试 alpha_beta depth={depth} ...")
        move, nodes, elapsed = ai_black.alpha_beta(game, depth)
        move_str = f"({move[0]},{move[1]})" if move else "None"
        md_lines.append(f"| {depth} | {move_str} | {nodes} | {elapsed:.1f} |")
        print(f"    -> 落子 {move_str}, 节点 {nodes}, 耗时 {elapsed:.1f} ms")

    md_lines.append("")

    # ---- MCTS 测试 ----
    md_lines.append("## 3. 蒙特卡洛树搜索（MCTS）\n")
    md_lines.append("| 时间限制 (秒) | 最佳落子 | 模拟次数 | 耗时 (ms) |")
    md_lines.append("|--------------|----------|---------|----------|")

    for t in mcts_times:
        print(f"  测试 mcts time_limit={t}s ...")
        move, sims, elapsed = ai_black.mcts(game, time_limit=t)
        move_str = f"({move[0]},{move[1]})" if move else "None"
        md_lines.append(f"| {t} | {move_str} | {sims} | {elapsed:.1f} |")
        print(f"    -> 落子 {move_str}, 模拟 {sims} 次, 耗时 {elapsed:.1f} ms")

    md_lines.append("")

    # ---- 对比总结 ----
    md_lines.append("## 4. 对比总结\n")
    md_lines.append("| 算法 | 优点 | 缺点 |")
    md_lines.append("|------|------|------|")
    md_lines.append("| Minimax | 结果精确，保证最优解 | 无剪枝，搜索量大，速度慢 |")
    md_lines.append("| Alpha-Beta | 剪枝大幅减少节点数 | 深度过大时仍然很慢 |")
    md_lines.append("| MCTS | 时间可控，适合复杂局面 | 随机性导致结果不稳定 |")

    # 输出完整报告
    report = "\n".join(md_lines)
    print("\n" + "=" * 60)
    print("  Markdown 性能报告")
    print("=" * 60)
    print(report)

    # 保存到文件
    with open("benchmark_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存到 benchmark_report.md")


# ============================================================
# 第五部分：主入口
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("  黑白棋（Reversi）")
    print("=" * 50)
    print()
    print("  请选择模式：")
    print("    1 - 启动 GUI 图形界面")
    print("    2 - 运行 Benchmark 性能测试")
    print()

    choice = input("  请输入选项 (1/2): ").strip()

    if choice == '1':
        # 启动 GUI 界面
        root = tk.Tk()
        app = ReversiGUI(root)
        root.update()          # 强制刷新一次界面，确保所有组件立即渲染
        root.mainloop()
    elif choice == '2':
        # 运行 Benchmark
        run_benchmark()
    else:
        print("  无效选项，请输入 1 或 2。")

# 这是一个示例 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。


def print_hi(name):
    # 在下面的代码行中使用断点来调试脚本。
    print(f'Hi, {name}')  # 按 Ctrl+F8 切换断点。


# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    print_hi('PyCharm')

# 访问 https://www.jetbrains.com/help/pycharm/ 获取 PyCharm 帮助
