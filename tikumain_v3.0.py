import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import random
import threading
import requests
from difflib import get_close_matches
import json


class FinanceApp:
    # 样式配置
    COLORS = {
        'primary': '#1890ff', 'success': '#52c41a', 'warning': '#faad14',
        'danger': '#ff4d4f', 'purple': '#722ed1', 'bg': '#f0f2f5',
        'choice': '#e6f7ff', 'fill': '#f6ffed', 'judge': '#fffbe6'
    }
    FONTS = {
        'title': ("微软雅黑", 26, "bold"), 'large': ("微软雅黑", 18, "bold"),
        'medium': ("微软雅黑", 12, "bold"), 'normal': ("微软雅黑", 11),
        'small': ("微软雅黑", 10), 'tiny': ("微软雅黑", 9)
    }
    BTN_STYLE = {"font": ("微软雅黑", 12, "bold"), "width": 25, "pady": 12, "relief": "flat", "cursor": "hand2"}

    def __init__(self, root):
        self.root = root
        self.root.title("金融学智能复习系统 v5.2")
        self.root.geometry("900x750")
        self.root.configure(bg=self.COLORS['bg'])

        # 路径配置
        self.config_path = self.get_resource_path('config.json')
        self.csv_paths = {
            'main': self.get_resource_path('题库.csv'),
            'choice': self.get_resource_path('题库_选择题.csv'),
            'fill': self.get_resource_path('题库_填空题.csv'),
            'judge': self.get_resource_path('题库_判断题.csv')
        }

        # 加载数据
        self.load_config()
        self.load_all_data()

        # 考试状态
        self.exam_state = {'questions': [], 'index': 0, 'score': 0, 'type': ''}

        # 主容器
        self.main_container = tk.Frame(self.root, bg=self.COLORS['bg'])
        self.main_container.pack(fill="both", expand=True)
        self.show_main_menu()

    def get_resource_path(self, relative_path):
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, relative_path)

    # ================= 数据加载 =================
    def load_config(self):
        default = {"api_url": "https://api.siliconflow.cn/v1/chat/completions",
                   "model": "Qwen/Qwen2.5-7B-Instruct", "enable_reasoning": False}
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = {**default, **json.load(f)}
            else:
                self.config = default
        except:
            self.config = default
        self.config['api_key'] = os.environ.get('SILICON_API_KEY', '')

    def save_config(self):
        try:
            config_save = {k: v for k, v in self.config.items() if k != 'api_key'}
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_save, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def load_all_data(self):
        # 主题库
        try:
            df = pd.read_csv(self.csv_paths['main'], encoding='utf-8-sig')
            self.quiz_dict = dict(zip(df['题目'], df['题目的文字答案']))
            self.questions = list(self.quiz_dict.keys())
        except:
            self.quiz_dict, self.questions = {}, []

        # 分类题库
        self.categorized = {}
        configs = [
            ('choice', ['stem', 'A', 'B', 'C', 'D', 'answer', 'type']),
            ('fill', ['stem', 'answer']),
            ('judge', ['stem', 'answer'])
        ]
        for key, cols in configs:
            try:
                df = pd.read_csv(self.csv_paths[key], encoding='utf-8-sig', header=None, names=cols)
                self.categorized[key] = df.to_dict('records')
            except:
                self.categorized[key] = []

    def clear_screen(self):
        for w in self.main_container.winfo_children():
            w.destroy()

    # ================= 通用UI组件 =================
    def create_nav_bar(self, text, command, color):
        nav = tk.Frame(self.main_container, bg=color, height=40)
        nav.pack(fill="x")
        tk.Button(nav, text=text, command=command, bg=self.COLORS.get(
            {'#e6f7ff': 'primary', '#f6ffed': 'success', '#fffbe6': 'warning',
             '#f0e6ff': 'purple'}.get(color, 'primary'), self.COLORS['primary']),
                  fg="white", relief="flat").pack(side="left", padx=10, pady=5)
        return nav

    def create_question_card(self, parent, text):
        card = tk.Frame(parent, bg="white", padx=20, pady=20, relief="groove", borderwidth=1)
        card.pack(fill="x", pady=15)
        tk.Label(card, text=text, font=self.FONTS['medium'], wraplength=750,
                 bg="white", justify="left").pack(anchor="w")
        return card

    def show_result_popup(self, is_correct, user_ans, correct_ans, q_stem, next_callback):
        pop = tk.Toplevel(self.root)
        pop.title("答题结果")
        pop.geometry("500x400")
        pop.grab_set()
        pop.configure(bg=self.COLORS['bg'])

        color = self.COLORS['success'] if is_correct else self.COLORS['danger']
        text = "✅ 回答正确！" if is_correct else "❌ 回答错误"
        tk.Label(pop, text=text, font=("微软雅黑", 20, "bold"), bg=self.COLORS['bg'], fg=color).pack(pady=20)

        info = tk.Frame(pop, bg="white", padx=20, pady=15)
        info.pack(fill="x", padx=20, pady=10)
        tk.Label(info, text=f"你的答案：{user_ans or '未作答'}", font=self.FONTS['normal'],
                 bg="white", anchor="w", wraplength=400).pack(fill="x", pady=5)
        tk.Label(info, text=f"正确答案：{correct_ans}", font=("微软雅黑", 11, "bold"),
                 bg="white", fg=self.COLORS['success'], anchor="w", wraplength=400).pack(fill="x", pady=5)

        btns = tk.Frame(pop, bg=self.COLORS['bg'])
        btns.pack(pady=20)
        tk.Button(btns, text="🤖 AI解析", command=lambda: self.open_ai_win(q_stem, correct_ans),
                  bg=self.COLORS['purple'], fg="white", font=self.FONTS['small'], width=12, pady=8).pack(side="left",
                                                                                                         padx=10)
        tk.Button(btns, text="下一题 →", command=lambda: [pop.destroy(), next_callback()],
                  bg=self.COLORS['primary'], fg="white", font=self.FONTS['small'], width=12, pady=8).pack(side="left",
                                                                                                          padx=10)

    def show_summary(self, title, color, total, score, retry_cmd, back_cmd):
        self.clear_screen()
        tk.Frame(self.main_container, bg=color, height=40).pack(fill="x")

        content = tk.Frame(self.main_container, bg=self.COLORS['bg'], padx=30, pady=30)
        content.pack(fill="both", expand=True)

        accuracy = (score / total * 100) if total > 0 else 0
        tk.Label(content, text=f"🎉 {title}完成！", font=("微软雅黑", 24, "bold"),
                 bg=self.COLORS['bg'],
                 fg=color if color and color.startswith('#') and len(color) == 7 else self.COLORS['primary']).pack(
            pady=20)

        for text, fg in [(f"总题数：{total} 题", None), (f"正确数：{score} 题", self.COLORS['success'])]:
            tk.Label(content, text=text, font=("微软雅黑", 14), bg=self.COLORS['bg'],
                     fg=fg or 'black').pack(pady=5)

        acc_color = self.COLORS['success'] if accuracy >= 60 else self.COLORS['danger']
        tk.Label(content, text=f"正确率：{accuracy:.1f}%", font=self.FONTS['large'],
                 bg=self.COLORS['bg'], fg=acc_color).pack(pady=15)

        btns = tk.Frame(content, bg=self.COLORS['bg'])
        btns.pack(pady=30)
        for text, cmd, bg in [("🔄 再练一次", retry_cmd, self.COLORS['primary']),
                              ("🏠 返回菜单", back_cmd, self.COLORS['purple'])]:
            tk.Button(btns, text=text, command=cmd, bg=bg, fg="white",
                      font=self.FONTS['medium'], width=15, pady=10).pack(side="left", padx=15)

    # ================= 主菜单 =================
    def show_main_menu(self):
        self.clear_screen()
        frame = tk.Frame(self.main_container, bg=self.COLORS['bg'])
        frame.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(frame, text="🏦 金融学智能复习系统", font=self.FONTS['title'],
                 bg=self.COLORS['bg'], fg=self.COLORS['primary']).pack(pady=10)

        status = f"当前模型：{self.config.get('model', '未配置')}"
        if not self.config.get('api_key'):
            status += " | ⚠️ 未配置API密钥"
        tk.Label(frame, text=status, font=self.FONTS['small'], bg=self.COLORS['bg'], fg="#999").pack(pady=(0, 30))

        buttons = [("🔍 题库检索模式", self.show_search_mode, '#40a9ff'),
                   ("📝 模拟刷题模式", self.show_practice_menu, self.COLORS['success']),
                   ("⚙️ API设置", self.show_settings, self.COLORS['purple'])]
        for text, cmd, bg in buttons:
            tk.Button(frame, text=text, command=cmd, bg=bg, fg="white", **self.BTN_STYLE).pack(pady=10)

    # ================= 设置界面 =================
    def show_settings(self):
        self.clear_screen()
        self.create_nav_bar("← 返回主菜单", self.show_main_menu, "#f0e6ff")

        content = tk.Frame(self.main_container, bg=self.COLORS['bg'], padx=40, pady=30)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="⚙️ API配置设置", font=self.FONTS['large'], bg=self.COLORS['bg']).pack(pady=(0, 20))

        # 安全提示
        warn = tk.Frame(content, bg="#fff7e6", relief="solid", borderwidth=1, padx=15, pady=12)
        warn.pack(fill="x", pady=15)
        tk.Label(warn, text="🔐 安全提示", font=("微软雅黑", 11, "bold"), bg="#fff7e6", fg="#ff7a45").pack(anchor="w")
        tk.Label(warn, text="• API密钥不会保存到文件，每次启动需重新输入\n• 推荐：设置环境变量 SILICON_API_KEY",
                 font=self.FONTS['tiny'], bg="#fff7e6", fg="#666", justify="left").pack(anchor="w", pady=(5, 0))

        # 输入字段
        self.settings_entries = {}
        fields = [('api_key', 'API密钥：', True), ('api_url', 'API端点：', False), ('model', '模型名称：', False)]
        for key, label, is_pwd in fields:
            frame = tk.Frame(content, bg=self.COLORS['bg'])
            frame.pack(fill="x", pady=15)
            tk.Label(frame, text=label, font=("微软雅黑", 11, "bold"), bg=self.COLORS['bg'], width=12, anchor="w").pack(
                side="left")
            entry = ttk.Entry(frame, font=self.FONTS['small'], show="*" if is_pwd else "")
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            entry.insert(0, self.config.get(key, ''))
            self.settings_entries[key] = entry
            if is_pwd:
                self.key_visible = False

                def toggle(e=entry):
                    self.key_visible = not self.key_visible
                    e.config(show="" if self.key_visible else "*")

                tk.Button(frame, text="🔒", command=toggle, width=3).pack(side="left", padx=5)

        # 推理模式
        reason_frame = tk.Frame(content, bg=self.COLORS['bg'])
        reason_frame.pack(fill="x", pady=15)
        tk.Label(reason_frame, text="推理模式：", font=("微软雅黑", 11, "bold"), bg=self.COLORS['bg'], width=12,
                 anchor="w").pack(side="left")
        self.reasoning_var = tk.BooleanVar(value=self.config.get('enable_reasoning', False))
        tk.Checkbutton(reason_frame, text="启用深度推理（更慢但更准确）", variable=self.reasoning_var,
                       bg=self.COLORS['bg'], font=self.FONTS['small']).pack(side="left")

        # 快捷模型选择
        tk.Label(content, text="常用模型快捷选择：", font=self.FONTS['small'], bg=self.COLORS['bg']).pack(anchor="w",
                                                                                                         pady=(20, 5))
        models_frame = tk.Frame(content, bg=self.COLORS['bg'])
        models_frame.pack(fill="x", pady=5)

        models = [("Qwen2.5-7B", "Qwen/Qwen2.5-7B-Instruct", True),
                  ("Qwen2-7B", "Qwen/Qwen2-7B-Instruct", False),
                  ("deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B", False)]
        for name, model, recommended in models:
            bg = "#ffe58f" if recommended else "#e6f7ff"
            text = f"{name}\n⭐ 推荐" if recommended else name
            tk.Button(models_frame, text=text,
                      command=lambda m=model: self.settings_entries['model'].delete(0, tk.END) or self.settings_entries[
                          'model'].insert(0, m),
                      bg=bg, relief="flat", padx=10, pady=5).pack(side="left", padx=5)

        if models[0][2]:
            tk.Label(content, text="💡 Qwen2.5-7B：孩子们，牢大帮你们测试过了，用这个，轻量快速且免费，且不开推理模式",
                     font=self.FONTS['tiny'], bg=self.COLORS['bg'], fg="#ff0400").pack(anchor="w", pady=(2, 5))

        # 按钮
        btns = tk.Frame(content, bg=self.COLORS['bg'])
        btns.pack(pady=20)
        tk.Button(btns, text="💾 保存配置", command=self.save_settings, bg=self.COLORS['success'],
                  fg="white", font=self.FONTS['medium'], width=12, pady=8).pack(side="left", padx=10)
        tk.Button(btns, text="🧪 测试连接", command=self.test_api_connection, bg=self.COLORS['primary'],
                  fg="white", font=self.FONTS['medium'], width=12, pady=8).pack(side="left", padx=10)

    def save_settings(self):
        for key in ['api_key', 'api_url', 'model']:
            self.config[key] = self.settings_entries[key].get().strip()
        self.config['enable_reasoning'] = self.reasoning_var.get()
        if not self.config['api_key']:
            messagebox.showwarning("提示", "API密钥不能为空！")
            return
        self.save_config()
        messagebox.showinfo("成功", "配置已保存！\n⚠️ API密钥只在本次运行时有效")

    def test_api_connection(self):
        if not self.config.get('api_key'):
            messagebox.showwarning("提示", "请先配置API密钥！")
            return
        win = tk.Toplevel(self.root)
        win.title("测试连接")
        win.geometry("400x200")
        win.grab_set()
        label = tk.Label(win, text="正在测试连接...", font=self.FONTS['medium'], pady=50)
        label.pack()

        def test():
            try:
                r = requests.post(self.config['api_url'], json={"model": self.config['model'],
                                                                "messages": [{"role": "user", "content": "你好"}],
                                                                "max_tokens": 10},
                                  headers={"Authorization": f"Bearer {self.config['api_key']}",
                                           "Content-Type": "application/json"}, timeout=10)
                msg = ("✅ 连接成功！\n模型响应正常", self.COLORS['success']) if r.status_code == 200 else (
                f"❌ 连接失败\n状态码: {r.status_code}", self.COLORS['danger'])
            except Exception as e:
                msg = (f"❌ 连接错误\n{str(e)[:50]}", self.COLORS['danger'])
            self.root.after(0, lambda: label.config(text=msg[0], fg=msg[1]))

        threading.Thread(target=test, daemon=True).start()

    # ================= 检索模式 =================
    def show_search_mode(self):
        self.clear_screen()
        self.create_nav_bar("← 返回主菜单", self.show_main_menu, self.COLORS['choice'])

        content = tk.Frame(self.main_container, bg=self.COLORS['bg'], padx=20, pady=10)
        content.pack(fill="both", expand=True)

        search_box = tk.Frame(content, bg=self.COLORS['bg'])
        search_box.pack(fill="x", pady=10)
        self.search_entry = ttk.Entry(search_box, font=self.FONTS['medium'])
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.search_entry.bind("<Return>", lambda e: self.exec_search())
        tk.Button(search_box, text="搜索", command=self.exec_search, bg="#40a9ff", fg="white", width=8).pack(
            side="left", padx=5)

        self.search_res = tk.Text(content, font=self.FONTS['normal'], wrap="word", padx=15, pady=15)
        self.search_res.pack(fill="both", expand=True, pady=10)
        self.search_res.tag_config("q_tag", foreground=self.COLORS['primary'], font=("微软雅黑", 11, "bold"))

        tk.Button(content, text="🤖 AI 解析选中或第一题", command=lambda: self.start_ai_flow(self.search_res),
                  bg=self.COLORS['success'], fg="white", font=self.FONTS['medium'], pady=10).pack(fill="x")

    def exec_search(self):
        kw = self.search_entry.get().strip()
        self.search_res.delete(1.0, tk.END)
        if not kw:
            return
        res = [q for q in self.questions if kw in q] or get_close_matches(kw, self.questions, n=3, cutoff=0.2)
        for q in res:
            self.search_res.insert(tk.END, f"【题目】：{q}\n", "q_tag")
            self.search_res.insert(tk.END, f"【答案】：{self.quiz_dict[q]}\n{'-' * 50}\n")

    # ================= 刷题菜单 =================
    def show_practice_menu(self):
        self.clear_screen()
        self.create_nav_bar("← 返回主菜单", self.show_main_menu, self.COLORS['fill'])

        frame = tk.Frame(self.main_container, bg=self.COLORS['bg'])
        frame.place(relx=0.5, rely=0.45, anchor="center")
        tk.Label(frame, text="选择练习模式", font=self.FONTS['large'], bg=self.COLORS['bg']).pack(pady=20)

        btn_s = {"font": ("微软雅黑", 11, "bold"), "width": 22, "pady": 10, "relief": "flat"}
        tk.Button(frame, text="🎲 随机挑战 (15题)", command=self.show_type_select,
                  bg=self.COLORS['purple'], fg="white", **btn_s).pack(pady=10)
        tk.Button(frame, text="⚙️ 自定义选题", command=self.show_custom_select,
                  bg=self.COLORS['warning'], fg="white", **btn_s).pack(pady=10)

    def show_type_select(self):
        self.clear_screen()
        self.create_nav_bar("← 返回", self.show_practice_menu, "#f0e6ff")

        frame = tk.Frame(self.main_container, bg=self.COLORS['bg'])
        frame.place(relx=0.5, rely=0.45, anchor="center")
        tk.Label(frame, text="🎯 选择题型", font=("微软雅黑", 22, "bold"),
                 bg=self.COLORS['bg'], fg=self.COLORS['purple']).pack(pady=30)

        btn_style = {"font": ("微软雅黑", 13, "bold"), "width": 20, "pady": 15, "relief": "flat", "cursor": "hand2"}
        types = [('choice', '📋 选择题', self.COLORS['primary']),
                 ('fill', '✏️ 填空题', self.COLORS['success']),
                 ('judge', '✅ 判断题', self.COLORS['warning'])]
        for key, text, bg in types:
            count = len(self.categorized.get(key, []))
            tk.Button(frame, text=f"{text}\n({count}题可用)", command=lambda k=key: self.start_typed_exam(k),
                      bg=bg, fg="white", **btn_style).pack(pady=12)

    # ================= 统一考试逻辑 =================

    # ================= 统一考试逻辑 =================
    def start_typed_exam(self, exam_type):
        questions = self.categorized.get(exam_type, [])
        if not questions:
            messagebox.showwarning("提示", f"{exam_type}题库为空！")
            return
        self.exam_state = {
            'type': exam_type,
            'questions': random.sample(questions, min(15, len(questions))),
            'index': 0,
            'score': 0
        }
        self.render_typed_page()

    def render_typed_page(self):
        self.clear_screen()
        state = self.exam_state
        q_data = state['questions'][state['index']]
        exam_type = state['type']

        # 颜色配置
        colors = {'choice': self.COLORS['choice'], 'fill': self.COLORS['fill'], 'judge': self.COLORS['judge']}
        type_colors = {'choice': self.COLORS['primary'], 'fill': self.COLORS['success'],
                       'judge': self.COLORS['warning']}
        type_names = {'choice': '选择题', 'fill': '填空题', 'judge': '判断题'}

        # 导航栏
        nav = tk.Frame(self.main_container, bg=colors[exam_type], height=40)
        nav.pack(fill="x")
        tk.Button(nav, text="← 退出练习", command=self.show_type_select,
                  bg=self.COLORS['danger'], fg="white", relief="flat").pack(side="left", padx=10, pady=5)
        progress = f"进度：{state['index'] + 1} / {len(state['questions'])} | 得分：{state['score']}"
        tk.Label(nav, text=progress, bg=colors[exam_type], font=self.FONTS['small']).pack(side="right", padx=10)

        # 内容区域
        content = tk.Frame(self.main_container, bg=self.COLORS['bg'], padx=30, pady=20)
        content.pack(fill="both", expand=True)

        # 题型标签
        q_type_str = str(q_data.get('type', '单选题')) if exam_type == 'choice' else type_names[exam_type]
        is_multi = '多选' in q_type_str
        label_color = self.COLORS['danger'] if is_multi else type_colors[exam_type]
        tk.Label(content, text=f"【{q_type_str}】", font=("微软雅黑", 11, "bold"),
                 bg=self.COLORS['bg'], fg=label_color).pack(anchor="w")

        # 题目卡片
        self.create_question_card(content, q_data['stem'])

        # 根据题型渲染选项
        if exam_type == 'choice':
            self._render_choice_options(content, q_data, is_multi)
        elif exam_type == 'fill':
            self._render_fill_input(content, q_data)
        else:
            self._render_judge_options(content)

        # 提交按钮
        btn_frame = tk.Frame(content, bg=self.COLORS['bg'])
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="✅ 提交答案", command=lambda: self.submit_typed_answer(q_data),
                  bg=type_colors[exam_type], fg="white", font=self.FONTS['medium'],
                  width=15, pady=10, cursor="hand2").pack()

    def _render_choice_options(self, parent, q_data, is_multi):
        """渲染选择题选项"""
        options_frame = tk.Frame(parent, bg=self.COLORS['bg'], pady=10)
        options_frame.pack(fill="x")

        if is_multi:
            self.choice_vars = {}
            for key in ['A', 'B', 'C', 'D']:
                opt = q_data.get(key, '')
                if opt and str(opt).strip() and str(opt) != 'nan':
                    var = tk.BooleanVar(value=False)
                    self.choice_vars[key] = var
                    opt_frame = tk.Frame(options_frame, bg="white", pady=8, padx=15)
                    opt_frame.pack(fill="x", pady=5)
                    tk.Checkbutton(opt_frame, text=f"{key}. {opt}", variable=var,
                                   font=self.FONTS['normal'], bg="white",
                                   activebackground="#e6f7ff", anchor="w", cursor="hand2").pack(fill="x", anchor="w")
            hint = "💡 多选题请选择所有正确选项"
        else:
            self.choice_var = tk.StringVar(value="")
            for key in ['A', 'B', 'C', 'D']:
                opt = q_data.get(key, '')
                if opt and str(opt).strip() and str(opt) != 'nan':
                    opt_frame = tk.Frame(options_frame, bg="white", pady=8, padx=15)
                    opt_frame.pack(fill="x", pady=5)
                    tk.Radiobutton(opt_frame, text=f"{key}. {opt}", variable=self.choice_var,
                                   value=key, font=self.FONTS['normal'], bg="white",
                                   activebackground="#e6f7ff", anchor="w", cursor="hand2").pack(fill="x", anchor="w")
            hint = "💡 单选题请选择一个正确选项"

        tk.Label(parent, text=hint, font=self.FONTS['tiny'], bg=self.COLORS['bg'], fg="#999").pack(anchor="w", pady=10)

    def _render_fill_input(self, parent, q_data):
        """渲染填空题输入"""
        answer_str = str(q_data.get('answer', ''))
        num_blanks = len(answer_str.split('|'))

        tk.Label(parent, text=f"请填写答案（共{num_blanks}个空，用 | 分隔多个答案）：",
                 bg=self.COLORS['bg'], font=self.FONTS['small']).pack(anchor="w", pady=(20, 5))

        self.fill_entry = ttk.Entry(parent, font=self.FONTS['medium'])
        self.fill_entry.pack(fill="x", pady=10, ipady=8)
        self.fill_entry.focus()
        self.fill_entry.bind("<Return>", lambda e: self.submit_typed_answer(q_data))

        tk.Label(parent, text="💡 多个空请用 | 分隔，如：答案1 | 答案2",
                 font=self.FONTS['tiny'], bg=self.COLORS['bg'], fg="#999").pack(anchor="w", pady=5)

    def _render_judge_options(self, parent):
        """渲染判断题选项"""
        options_frame = tk.Frame(parent, bg=self.COLORS['bg'], pady=20)
        options_frame.pack(fill="x")

        self.judge_var = tk.StringVar(value="")

        for value, text, bg_color, active_bg in [("对", "✅ 对", "#f6ffed", "#d9f7be"),
                                                 ("错", "❌ 错", "#fff2f0", "#ffccc7")]:
            frame = tk.Frame(options_frame, bg=bg_color, pady=15, padx=30)
            frame.pack(side="left", expand=True, fill="x", padx=20)
            tk.Radiobutton(frame, text=text, variable=self.judge_var, value=value,
                           font=("微软雅黑", 14, "bold"), bg=bg_color,
                           activebackground=active_bg, cursor="hand2").pack()

    def submit_typed_answer(self, q_data):
        """统一提交答案处理"""
        exam_type = self.exam_state['type']
        correct_answer = str(q_data.get('answer', '')).strip()

        # 获取用户答案并判断正确性
        if exam_type == 'choice':
            q_type_str = str(q_data.get('type', '单选题'))
            is_multi = '多选' in q_type_str
            if is_multi:
                selected = [k for k, v in self.choice_vars.items() if v.get()]
                user_answer = ''.join(sorted(selected))
            else:
                user_answer = self.choice_var.get().upper()

            if not user_answer:
                messagebox.showwarning("提示", "请先选择答案！")
                return

            correct_set = set(correct_answer.upper().replace(',', '').replace(' ', ''))
            user_set = set(user_answer)
            is_correct = (user_set == correct_set)

        elif exam_type == 'fill':
            user_answer = self.fill_entry.get().strip()
            if not user_answer:
                messagebox.showwarning("提示", "请先填写答案！")
                return

            user_parts = [p.strip().lower() for p in user_answer.split('|')]
            correct_parts = [p.strip().lower() for p in correct_answer.split('|')]
            matched = sum(1 for u in user_parts if any(u in c or c in u for c in correct_parts))
            is_correct = matched >= len(correct_parts) * 0.8

        else:  # judge
            user_answer = self.judge_var.get()
            if not user_answer:
                messagebox.showwarning("提示", "请先选择答案！")
                return
            is_correct = (user_answer == correct_answer)

        # 更新分数
        if is_correct:
            self.exam_state['score'] += 1

        # 显示结果弹窗
        self.show_result_popup(is_correct, user_answer, correct_answer, q_data['stem'], self._go_next_question)

    def _go_next_question(self):
        """进入下一题或显示总结"""
        state = self.exam_state
        if state['index'] < len(state['questions']) - 1:
            state['index'] += 1
            self.render_typed_page()
        else:
            self._show_typed_summary()

    def _show_typed_summary(self):
        """显示答题总结"""
        state = self.exam_state
        exam_type = state['type']

        colors = {'choice': self.COLORS['choice'], 'fill': self.COLORS['fill'], 'judge': self.COLORS['judge']}
        titles = {'choice': '选择题', 'fill': '填空题', 'judge': '判断题'}

        self.show_summary(
            title=titles[exam_type],
            color=colors[exam_type],
            total=len(state['questions']),
            score=state['score'],
            retry_cmd=lambda: self.start_typed_exam(exam_type),
            back_cmd=self.show_type_select
        )

    # ================= 自定义选题 =================
    def show_custom_select(self):
        self.clear_screen()
        nav = tk.Frame(self.main_container, bg=self.COLORS['judge'], height=40)
        nav.pack(fill="x")
        tk.Button(nav, text="← 返回", command=self.show_practice_menu,
                  bg=self.COLORS['warning'], fg="white", relief="flat").pack(side="left", padx=10, pady=5)

        tk.Label(self.main_container, text="请勾选想练习的题目：",
                 font=self.FONTS['medium'], bg=self.COLORS['bg']).pack(pady=10)

        # 滚动列表
        list_container = tk.Frame(self.main_container, padx=20)
        list_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_container, bg="white")
        scroll_y = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll_y.set)

        self.custom_vars = {}
        for q in self.questions:
            v = tk.BooleanVar()
            self.custom_vars[q] = v
            tk.Checkbutton(scroll_frame, text=q[:90] + "..." if len(q) > 90 else q,
                           variable=v, bg="white", font=self.FONTS['tiny']).pack(anchor="w", pady=2)

        canvas.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        tk.Button(self.main_container, text="开始练习所选题目", command=self.start_custom_practice,
                  bg=self.COLORS['success'], fg="white", font=self.FONTS['medium'], pady=12).pack(fill="x", padx=20,
                                                                                                  pady=15)

    def start_custom_practice(self):
        selected = [q for q, v in self.custom_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("提示", "请先勾选题目！")
            return
        self.custom_exam_qs = selected
        self.custom_idx = 0
        self.render_custom_exam_page()

    def render_custom_exam_page(self):
        self.clear_screen()
        q_text = self.custom_exam_qs[self.custom_idx]

        tk.Label(self.main_container, text=f"进度：{self.custom_idx + 1} / {len(self.custom_exam_qs)}",
                 bg=self.COLORS['bg'], fg="#999").pack(pady=5)

        self.create_question_card(self.main_container, q_text)

        tk.Label(self.main_container, text="请输入答案：", bg=self.COLORS['bg'],
                 font=self.FONTS['small']).pack(anchor="w", padx=35, pady=(20, 0))
        self.custom_entry = ttk.Entry(self.main_container, font=self.FONTS['medium'])
        self.custom_entry.pack(fill="x", padx=35, pady=10, ipady=5)
        self.custom_entry.focus()

        ctrl_box = tk.Frame(self.main_container, bg=self.COLORS['bg'])
        ctrl_box.pack(pady=20)
        tk.Button(ctrl_box, text="提交并看解析", command=lambda: self.judge_custom_answer(q_text),
                  bg=self.COLORS['primary'], fg="white", font=self.FONTS['small'], width=15, pady=8).pack(side="left",
                                                                                                          padx=10)
        tk.Button(ctrl_box, text="退出练习", command=self.show_practice_menu,
                  bg=self.COLORS['danger'], fg="white", font=self.FONTS['small'], width=10).pack(side="left", padx=10)

    def judge_custom_answer(self, q):
        u_ans = self.custom_entry.get().strip()
        t_ans = self.quiz_dict.get(q, "")
        is_ok = u_ans.lower() in t_ans.lower() if u_ans else False

        pop = tk.Toplevel(self.root)
        pop.title("结果判定")
        pop.geometry("450x380")
        pop.grab_set()

        tk.Label(pop, text="判定结果", font=self.FONTS['small']).pack(pady=10)
        tk.Label(pop, text="✅ 答对了！" if is_ok else "❌ 需努力",
                 font=self.FONTS['large'], fg=self.COLORS['success'] if is_ok else self.COLORS['danger']).pack()

        ans_box = tk.Text(pop, font=self.FONTS['small'], height=6, bg="#fafafa", padx=10, pady=10)
        ans_box.pack(fill="x", padx=20, pady=10)
        ans_box.insert(tk.END, f"您的答案：{u_ans if u_ans else '未填'}\n\n标准答案：{t_ans}")
        ans_box.config(state="disabled")

        btn_f = tk.Frame(pop)
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="🤖 AI 极速解析", command=lambda: self.open_ai_win(q, t_ans),
                  bg=self.COLORS['purple'], fg="white", padx=15).pack(side="left", padx=5)

        def go_next():
            pop.destroy()
            if self.custom_idx < len(self.custom_exam_qs) - 1:
                self.custom_idx += 1
                self.render_custom_exam_page()
            else:
                messagebox.showinfo("完成", "你过关！(得意地")
                self.show_practice_menu()

        tk.Button(btn_f, text="下一题 →", command=go_next,
                  bg=self.COLORS['primary'], fg="white", padx=20).pack(side="left", padx=5)

    # ================= AI 模块 =================
    def start_ai_flow(self, text_widget):
        if not self.config.get('api_key'):
            messagebox.showwarning("提示", "请先在设置中配置API密钥！")
            return

        try:
            q = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except:
            content = text_widget.get(1.0, tk.END).strip()
            q = content.split('\n')[0].replace("【题目】：", "").strip() if "【题目】" in content else ""

        if not q or len(q) < 2:
            messagebox.showwarning("提示", "请选中题目文字后再点击解析！")
            return
        self.open_ai_win(q, self.quiz_dict.get(q, "本地库无对应答案"))

    def open_ai_win(self, q, a):
        if not self.config.get('api_key'):
            messagebox.showwarning("提示", "请先在设置中配置API密钥！")
            return

        ai_w = tk.Toplevel(self.root)
        ai_w.title(f"AI解析 - {self.config['model']}")
        ai_w.geometry("600x550")

        txt = tk.Text(ai_w, font=self.FONTS['normal'], wrap="word", padx=15, pady=15)
        txt.pack(fill="both", expand=True)
        txt.insert(tk.END, "正在连接您的外置大脑...\n\n")

        threading.Thread(target=self.call_api, args=(q, a, txt), daemon=True).start()

    def call_api(self, q, a, widget):
        prompt = f"""题目：{q}
参考答案：{a}
你是只猫娘，给出详细且好懂的解析，并指出考点。纯文本，不要markdown格式，星号也不要，对于选择题最好的回答方式是针对每一个选项回答为什么正确或者错误。说话要带上"喵"或者颜文字，适量即可"""

        payload = {
            "model": self.config['model'],
            "messages": [
                {"role": "system", "content": """你是一只可爱的猫娘，说话要带上"喵"的后缀。"""},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        if self.config.get('enable_reasoning', False):
            payload["enable_thinking"] = True

        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }

        try:
            r = requests.post(self.config['api_url'], json=payload, headers=headers, timeout=20)
            if r.status_code == 200:
                ans = r.json()['choices'][0]['message']['content']
            else:
                ans = f"API 返回错误 (状态码:{r.status_code})\n请检查API配置是否正确"
        except Exception as err:
            ans = f"网络错误: {err}\n\n请检查:\n1. API密钥是否正确\n2. 网络连接是否正常\n3. API端点是否可访问"

        self.root.after(0, lambda: self._update_ai_result(widget, ans))

    def _update_ai_result(self, widget, content):
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, content)


if __name__ == "__main__":
    root = tk.Tk()
    # 窗口居中
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"900x750+{int((sw - 900) / 2)}+{int((sh - 750) / 2)}")

    app = FinanceApp(root)
    root.mainloop()
