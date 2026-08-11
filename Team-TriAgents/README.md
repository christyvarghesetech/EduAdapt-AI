

# 🎓 EduAdapt AI

### An Agentic AI-Powered Personalized Learning Platform

---

## 👥 Team

**Team Name:** TriAgents

### Team Members
Christy Varghese|Backend & Database|
Dilna Ditto M|AI & Agent Development|
Rohan C Roby|Frontend & UI/UX|
---

## 📌 Project Title

**EduAdapt AI – An Agentic AI Personalized Learning Platform**

---

## ❗ Problem Statement

Traditional online learning platforms generally provide the same learning content and learning paths to all students.

However, every student has different:
- Learning abilities
- Knowledge levels
- Strengths and weaknesses
- Learning speeds
- Areas that require additional practice

When a student performs poorly in a particular topic, conventional systems may only display the score without understanding the underlying knowledge gap or automatically adapting the learning process.

Students therefore need a system that can continuously understand their performance, identify knowledge gaps, provide personalized explanations, generate targeted assessments, and dynamically adapt their learning plan.

---

## 💡 Our Solution

**EduAdapt AI** is an Agentic AI-powered personalized learning platform that acts as an autonomous AI learning companion for students.

Instead of using a single chatbot, EduAdapt AI uses multiple specialized AI agents that collaborate to understand the learner and continuously adapt the learning experience.

The system follows a continuous learning loop:

**Assess → Analyze → Teach → Practice → Evaluate → Adapt**

The platform can:

1. Assess the student's current knowledge.
2. Identify weak and strong areas.
3. Provide personalized explanations.
4. Generate topic-specific quizzes.
5. Analyze quiz performance.
6. Track learning progress.
7. Automatically update the student's learning plan.

---

## ⭐ Key Features

### 1. 📝 Initial Assessment
The platform conducts an assessment to understand the student's current knowledge level.

### 2. 🧠 Knowledge Gap Detection
The system analyzes the student's answers and identifies topics where the student needs improvement.

### 3. 👨‍🏫 AI Personalized Tutor
The Tutor Agent explains difficult concepts according to the student's knowledge level and learning needs.

### 4. ❓ Adaptive Quiz Generation
The Quiz Agent generates questions based on the student's weak areas.

### 5. 📊 Performance Analysis
The system tracks quiz scores and learning performance over time.

### 6. 📅 Personalized Study Plan
The Planner Agent creates and updates a study plan based on the student's progress.

### 7. 🔄 Continuous Adaptation
The learning path changes automatically as the student's performance changes.

### 8. 💬 AI Learning Assistant
Students can interact with the AI to ask questions and receive explanations related to their learning topics.

---

# 🤖 Agent Workflow

```text
                    ┌─────────────────┐
                    │     Student     │
                    └────────┬────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Learning Manager   │
                  │       Agent         │
                  └─────────┬───────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │ Assessment │ │   Tutor    │ │    Quiz    │
      │   Agent    │ │   Agent    │ │   Agent    │
      └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ Progress & Planning │
                  │       Agent         │
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ Personalized Study  │
                  │       Plan          │
                  └─────────┬───────────┘
                            │
                            ▼
                     ┌────────────┐
                     │  Student   │
                     └────────────┘
🛠️ Tech Stack

# Frontend
- React.js
- HTML5
- CSS3
- JavaScript

# Backend
- Python
- FastAPI

# AI / LLM
- LLM API
- Prompt Engineering
- RAG

##Agent Framework
- LangGraph

# Tools / APIs
- LLM API
- REST APIs

# Database
- SQLite
