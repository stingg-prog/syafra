# 🛍️ SYAFRA – Modern Django E-commerce Platform

> A production-ready full-stack e-commerce platform built with Python and Django, featuring secure payment integration, cloud deployment, inventory management, and responsive design.

---

## 🌐 Live Demo

🔗 **Website:** https://syafra.com

👨‍💻 **Portfolio:** https://syamraj-portfolio.onrender.com/

💼 **LinkedIn:** https://www.linkedin.com/in/syamraj-r-53670a419/

💻 **GitHub Repository:**
https://github.com/stingg-prog/syafra

---

# ✨ Features

- 🔐 User Authentication & Authorization
- 🛒 Shopping Cart
- 📦 Product Management
- 📑 Order Management
- 💳 Secure Payment Gateway Integration
- 📧 Automated Email Notifications
- 📊 Admin Dashboard
- 📱 Fully Responsive UI
- 📦 Inventory Management
- ☁️ Cloud Deployment

---

# 🛠️ Tech Stack

## Backend

- Python
- Django

## Frontend

- HTML5
- CSS3
- JavaScript
- Bootstrap

## Database

- Neon PostgreSQL

## Cloud & Deployment

- Render
- Cloudinary

## Version Control

- Git
- GitHub

---

# 🚀 Architecture

Frontend

⬇️

Django Backend

⬇️

Neon PostgreSQL Database

⬇️

Cloudinary Media Storage

⬇️

Render Production Deployment

---

# 📦 Core Modules

- User Authentication
- Product Catalog
- Shopping Cart
- Checkout
- Order Processing
- Payment Integration
- Email Automation
- Admin Management
- Inventory Control

---

# ⚙️ Installation

```bash
git clone https://github.com/stingg-prog/syafra.git
cd syafra/syafra

python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The repository root contains the Git metadata and project-level tooling. The Django application, `manage.py`, Python dependencies, and its CSS build package are in the inner `syafra/` directory. The project notes and implementation reports are indexed in [`syafra/docs/`](syafra/docs/README.md).

### JavaScript tooling

- The repository-root `package.json` is for optional Playwright-based browser QA tools.
- `syafra/package.json` is the Django application's Tailwind CSS build toolchain. Run its CSS build scripts from the inner `syafra/` directory.

## Windows setup for the local Syafra AI Assistant

The assistant uses Ollama on the same Windows machine, so photo analysis runs locally without per-request API charges. Open PowerShell in the `syafra` folder and run:

    powershell -ExecutionPolicy Bypass -File .\setup_agent_windows.ps1

The script finds Ollama in its standard Windows install location or on `PATH`, downloads `qwen2.5vl:3b` if needed, creates a separate Windows virtual environment, installs the project dependencies, and starts the local server with loopback-only host settings. It leaves `.env` files untouched. For a local database, it applies all pending project migrations and offers to create a Django superuser if none exists. For a remote database, it asks you to type `MIGRATE` before applying only the product-material and assistant migrations, which add the material field plus the assistant's proposal and private-image tables. The project `.env` database settings remain in use; when those point to your live database, this local assistant can create approved listings on that site.

Open `http://127.0.0.1:8000/admin/ai-assistant/` and sign in with the existing Django admin account. Upload clothing photos, choose whether to group photos of the same item or create one product per photo, and describe what you want the assistant to do. Python prepares warm beige studio-style photos with angled sunlight. In the preview, enter the approved price and size stock as one `SIZE: quantity` per line; total stock is calculated automatically. The AI drafts the other product details from the photos. Review the photo and every field, optionally make supported prompt-based photo adjustments, then explicitly confirm to add the products and photos to the website. Keep the Windows server running while using the assistant; a Render-hosted Django process cannot reach Ollama on your PC.

The same assistant can answer questions from the current website content and prepare create, edit, or delete drafts for supported CMS records, including homepage sections, hero slides, banners, pages, navigation, FAQs, blogs, and related content. A deletion must name one specific record; the review shows linked records that may be affected. Every website change still requires your explicit confirmation. Arbitrary HTML, executable code, and source-code edits are not available through the assistant.

### Cloud AI for the Syafra assistant

The assistant is implemented in Python and can use Google Gemini for image analysis and draft generation when the Django app runs in the cloud. The Render Blueprint selects `SYAFRA_AGENT_PROVIDER=gemini` and `SYAFRA_AGENT_GEMINI_MODEL=gemini-3.5-flash-lite`; add `GEMINI_API_KEY` as a secret from Google AI Studio in the Render dashboard. Do not put the key in source control or send it in chat. Save and deploy the service after adding the secret. The free Gemini tier is limited and may use submitted prompts, product photos, and website context to improve Google products; review Google's current terms before enabling this provider. The cloud assistant will not use Ollama on your PC. To keep all images local, continue using the Windows Ollama setup above.

---

# 🌍 Deployment

The repository-root [`render.yaml`](render.yaml) is the single Render Blueprint for the existing `syafra` web service, with the Django app in the inner `syafra/` directory. Applying or syncing a Blueprint can change service configuration; the file does not change the current dashboard settings on its own. The Free plan has an ephemeral filesystem and does not support persistent disks, so keep Cloudinary credentials configured in the Render Dashboard for uploaded media. Secret values are never committed here.

Production deployment uses

- Render
- Neon PostgreSQL
- Cloudinary

---

# 📂 Project Structure

```
syafra/                     # Repository root
├── README.md
├── package.json            # Optional Playwright/browser QA tooling
├── render.yaml             # Canonical Render Blueprint
└── syafra/                 # Django project root
    ├── accounts/
    ├── cart/
    ├── cms/
    ├── docs/               # Project guides and implementation reports
    ├── orders/
    ├── products/
    ├── static/
    ├── templates/
    ├── manage.py
    ├── package.json        # Tailwind CSS build tooling
    └── requirements.txt
```

---

# 👨‍💻 Developed By

## SYAMRAJ R

**Python Full Stack Developer**

Founder — **SYAFRA**

🌐 Portfolio: [syamraj-portfolio.onrender.com](https://syamraj-portfolio.onrender.com)

💼 LinkedIn: [Syamraj R](https://www.linkedin.com/in/syamraj-r-53670a419/)

💻 GitHub: [stingg-prog](https://github.com/stingg-prog)

🛍️ Live Website: [syafra.com](https://syafra.com)

---

## ⭐ Support

Made with ❤️ using Python, Django, PostgreSQL (Neon), Render, and Cloudinary.

⭐ If you found this project helpful, please consider giving it a Star on GitHub!
