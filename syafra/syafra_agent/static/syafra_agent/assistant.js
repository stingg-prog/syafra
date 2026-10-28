(function () {
  "use strict";

  const app = document.getElementById("syafra-agent-app");
  if (!app) return;

  const form = document.getElementById("agent-prompt-form");
  const promptInput = document.getElementById("agent-prompt");
  const imageInput = document.getElementById("agent-images");
  const photoModeInput = document.getElementById("agent-photo-mode");
  const uploadPreview = document.getElementById("agent-upload-preview");
  const uploadCount = document.getElementById("agent-upload-count");
  const conversation = document.getElementById("agent-conversation");
  const liveStatus = document.getElementById("agent-live-status");
  const submitButton = document.getElementById("agent-submit");
  const previewPanel = document.getElementById("agent-preview-panel");
  const previewReply = document.getElementById("agent-preview-reply");
  const previewActions = document.getElementById("agent-preview-actions");
  const visualPreview = document.getElementById("agent-visual-preview");
  const expiryLabel = document.getElementById("agent-expiry");
  const confirmCheckbox = document.getElementById("agent-review-confirmation");
  const confirmButton = document.getElementById("agent-confirm-preview");
  const cancelButton = document.getElementById("agent-cancel-preview");
  const validationMessage = document.getElementById("agent-validation-message");
  const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;
  const fieldDefinitions = JSON.parse(document.getElementById("syafra-agent-field-definitions").textContent);
  const canCreateCategory = app.dataset.canCreateCategory === "true";
  const fieldLabels = {
    name: "പേര്", brand: "ബ്രാൻഡ്", category_id: "വിഭാഗം", new_category_name: "പുതിയ വിഭാഗത്തിന്റെ പേര്",
    condition: "നില", price: "വില", stock: "സ്റ്റോക്ക്", description: "വിവരണം", is_featured: "പ്രധാന ഉൽപ്പന്നം",
    material: "മെറ്റീരിയൽ", sizes: "സൈസ് അനുസരിച്ചുള്ള സ്റ്റോക്ക്", title: "തലക്കെട്ട്", subtitle: "ഉപതലക്കെട്ട്",
    overline: "ചെറിയ തലക്കെട്ട്", section_type: "Homepage വിഭാഗത്തിന്റെ തരം", is_active: "Website-ൽ കാണിക്കുക",
    display_order: "പ്രദർശന ക്രമം", section_id: "Homepage വിഭാഗം", image: "ചിത്രം", image_url: "ചിത്രത്തിന്റെ URL",
    button_text: "Button-ലെ എഴുത്ത്", button_url: "Button ലിങ്ക്", slug: "URL slug", content: "ഉള്ളടക്കം",
    summary: "ചുരുക്കം", meta_title: "SEO തലക്കെട്ട്", meta_description: "SEO വിവരണം", author_id: "രചയിതാവ്",
    question: "ചോദ്യം", answer: "ഉത്തരം", label: "ലേബൽ", url: "URL", parent_id: "Parent navigation ഇനം",
    placement: "Navigation സ്ഥാനം", is_external: "പുറത്തുള്ള ലിങ്ക്", is_mega_menu: "Mega menu പ്രവർത്തനക്ഷമമാക്കുക",
    collection_id: "Collection", product_id: "Product", testimonial_id: "Testimonial", lookbook_id: "Lookbook",
    homepage_section_id: "Homepage വിഭാഗം", category: "വിഭാഗം", page_type: "Page തരം", is_published: "പ്രസിദ്ധീകരിക്കുക",
    text: "എഴുത്ത്", color: "നിറം", bg_color: "പശ്ചാത്തല നിറം", alt_text: "ചിത്രത്തിന്റെ alt എഴുത്ത്",
    instagram_url: "Instagram URL", facebook_url: "Facebook URL", twitter_url: "X / Twitter URL",
    youtube_url: "YouTube URL", pinterest_url: "Pinterest URL", tiktok_url: "TikTok URL",
    email: "ഇമെയിൽ", phone: "ഫോൺ", contact_email: "ബന്ധപ്പെടാനുള്ള ഇമെയിൽ", contact_phone: "ബന്ധപ്പെടാനുള്ള ഫോൺ",
    business_address: "വിലാസം", business_hours: "പ്രവർത്തന സമയം", whatsapp_number: "WhatsApp നമ്പർ",
    delay_seconds: "താമസം (സെക്കൻഡ്)", scroll_percent: "Scroll ശതമാനം", show_on_mobile: "മൊബൈലിൽ കാണിക്കുക",
    show_on_desktop: "Desktop-ൽ കാണിക്കുക", hide_on_mobile: "മൊബൈലിൽ മറയ്ക്കുക", hide_on_desktop: "Desktop-ൽ മറയ്ക്കുക",
    padding_top: "മുകളിലെ ഇടവിട്ട്", padding_bottom: "താഴെയുള്ള ഇടവിട്ട്", margin: "Margin", border_radius: "മൂലയുടെ ആകൃതി",
    full_width: "മുഴുവൻ വീതിയിലും", footer_columns: "Footer നിരകൾ", copyright_text: "Copyright എഴുത്ത്",
    display_frequency: "കാണിക്കുന്ന ആവൃത്തി", popup_type: "Popup തരം", trigger: "പ്രവർത്തന നിബന്ധന",
    store_name: "സ്റ്റോറിന്റെ പേര്", tagline: "Tagline", enable_loader: "Loader പ്രവർത്തനക്ഷമമാക്കുക",
    loader_type: "Loader തരം", loader_color: "Loader നിറം", primary_color: "പ്രധാന നിറം", secondary_color: "രണ്ടാം നിറം",
    accent_color: "Accent നിറം", success_color: "വിജയ സന്ദേശത്തിന്റെ നിറം", warning_color: "മുന്നറിയിപ്പ് നിറം",
    danger_color: "പിശക് നിറം", info_color: "വിവര നിറം", background_color: "പശ്ചാത്തല നിറം", surface_color: "Surface നിറം",
    card_color: "Card നിറം", border_color: "Border നിറം", text_color: "എഴുത്തിന്റെ നിറം", muted_text_color: "മങ്ങിയ എഴുത്തിന്റെ നിറം",
    heading_font: "തലക്കെട്ടിന്റെ font", body_font: "സാധാരണ എഴുത്തിന്റെ font", font_size_scale: "Font വലുപ്പ അനുപാതം",
    heading_font_weight: "തലക്കെട്ടിന്റെ കനം", body_font_weight: "എഴുത്തിന്റെ കനം", letter_spacing: "അക്ഷര ഇടവിട്ട്",
    line_height: "വരി ഉയരം", primary_btn_bg: "പ്രധാന button പശ്ചാത്തലം", primary_btn_text: "പ്രധാന button എഴുത്ത്",
    primary_btn_border_radius: "പ്രധാന button മൂലയുടെ ആകൃതി", primary_btn_shadow: "പ്രധാന button നിഴൽ",
    primary_btn_hover_animation: "പ്രധാന button hover animation", secondary_btn_bg: "രണ്ടാം button പശ്ചാത്തലം",
    secondary_btn_text: "രണ്ടാം button എഴുത്ത്", header_style: "Header ശൈലി", sticky_header: "Header മുകളിൽ നിലനിർത്തുക",
    transparent_header: "സുതാര്യമായ header", mega_menu_enabled: "Mega menu പ്രവർത്തനക്ഷമമാക്കുക",
    mobile_menu_style: "Mobile menu ശൈലി", social_links_enabled: "Social links കാണിക്കുക",
    payment_icons_enabled: "Payment icons കാണിക്കുക", footer_newsletter_enabled: "Footer newsletter കാണിക്കുക",
    layout_style: "Layout ശൈലി", container_width: "Container വീതി", sidebar_width: "Sidebar വീതി",
    product_grid_layout: "Product grid ശൈലി", category_grid_layout: "Category grid ശൈലി", blog_layout: "Blog layout",
    spacing_scale: "ഇടവിട്ട് അളവ്", products_per_page: "ഒരു പേജിലെ products", default_sorting: "Default ക്രമീകരണം",
    wishlist_enabled: "Wishlist പ്രവർത്തനക്ഷമമാക്കുക", compare_enabled: "Product താരതമ്യം പ്രവർത്തനക്ഷമമാക്കുക",
    quick_view_enabled: "Quick view പ്രവർത്തനക്ഷമമാക്കുക", recently_viewed_enabled: "സമീപകാലത്ത് കണ്ടത് പ്രവർത്തനക്ഷമമാക്കുക",
    infinite_scroll_enabled: "തുടർച്ചയായ scroll പ്രവർത്തനക്ഷമമാക്കുക", pagination_style: "Pagination ശൈലി",
    image_zoom_enabled: "ചിത്രം zoom ചെയ്യുക", gallery_layout: "Product gallery ശൈലി", sticky_gallery_enabled: "Gallery മുകളിൽ നിലനിർത്തുക",
    sticky_buy_box_enabled: "വാങ്ങൽ ഭാഗം മുകളിൽ നിലനിർത്തുക", size_chart_enabled: "Size chart കാണിക്കുക",
    delivery_info_enabled: "Delivery വിവരം കാണിക്കുക", related_products_enabled: "ബന്ധപ്പെട്ട products കാണിക്കുക",
    recently_viewed_products_enabled: "സമീപകാലത്ത് കണ്ട products കാണിക്കുക", trust_badges_enabled: "വിശ്വാസ ബാഡ്ജുകൾ കാണിക്കുക",
    mini_cart_enabled: "Mini cart പ്രവർത്തനക്ഷമമാക്കുക", slide_cart_enabled: "Slide cart പ്രവർത്തനക്ഷമമാക്കുക",
    cart_notes_enabled: "Cart കുറിപ്പുകൾ പ്രവർത്തനക്ഷമമാക്കുക", shipping_progress_bar_enabled: "Shipping progress കാണിക്കുക",
    cross_sell_enabled: "Cross-sell പ്രവർത്തനക്ഷമമാക്കുക", upsell_enabled: "Upsell പ്രവർത്തനക്ഷമമാക്കുക",
    page_transitions_enabled: "Page transitions പ്രവർത്തനക്ഷമമാക്കുക", button_animations_enabled: "Button animation പ്രവർത്തനക്ഷമമാക്കുക",
    hover_effects_enabled: "Hover effect പ്രവർത്തനക്ഷമമാക്കുക", card_animations_enabled: "Card animation പ്രവർത്തനക്ഷമമാക്കുക",
    scroll_animations_enabled: "Scroll animation പ്രവർത്തനക്ഷമമാക്കുക", loading_animations_enabled: "Loading animation പ്രവർത്തനക്ഷമമാക്കുക",
    preview_mode: "Preview mode", seo_title: "SEO തലക്കെട്ട്", seo_description: "SEO വിവരണം", seo_keywords: "SEO keywords",
    link_url: "ലിങ്ക് URL", link_text: "ലിങ്ക് എഴുത്ത്", excerpt: "ചുരുക്ക വിവരണം", website: "Website",
    review: "അഭിപ്രായം", column_heading: "നിരയുടെ തലക്കെട്ട്", show_on_pages: "കാണിക്കേണ്ട pages", overlay_opacity: "Overlay അതാര്യത",
    image_position_x: "ചിത്രത്തിന്റെ X സ്ഥാനം", image_position_y: "ചിത്രത്തിന്റെ Y സ്ഥാനം", canonical_url: "Canonical URL",
    og_title: "Social share തലക്കെട്ട്", og_description: "Social share വിവരണം", twitter_title: "Twitter തലക്കെട്ട്",
    twitter_description: "Twitter വിവരണം", robots: "Search indexing നിർദ്ദേശം", show_on_tablet: "Tablet-ൽ മറയ്ക്കുക",
    hide_on_tablet: "Tablet-ൽ മറയ്ക്കുക", animation: "Animation", anchor_id: "Section anchor ID", container_width: "Container വീതി",
    secondary_btn_border_radius: "രണ്ടാം button മൂലയുടെ ആകൃതി", secondary_btn_shadow: "രണ്ടാം button നിഴൽ",
    secondary_btn_hover_animation: "രണ്ടാം button hover effect", footer_copyright: "Footer copyright എഴുത്ത്",
    whatsapp_default_message: "WhatsApp-ന്റെ default സന്ദേശം", maintenance_mode: "Maintenance mode",
    maintenance_message: "Maintenance സന്ദേശം", threads_url: "Threads URL", linkedin_url: "LinkedIn URL",
    icon: "Icon class", meta_keywords: "SEO keywords", headline: "പ്രധാന തലക്കെട്ട്", bio: "രചയിതാവിന്റെ പരിചയം",
    size: "Product size", link: "Instagram ലിങ്ക്", rating: "റേറ്റിംഗ് (1 മുതൽ 5 വരെ)", video_url: "Testimonial video URL",
    is_sticky: "മുകളിൽ നിലനിർത്തുക", dismissible: "അടയ്ക്കാൻ അനുവദിക്കുക", is_featured: "പ്രധാനമായി കാണിക്കുക",
  };
  const choiceLabels = {
    New: "പുതിയത്", Used: "ഉപയോഗിച്ചത്", Refurbished: "പുതുക്കിയത്", "Single image": "ഒറ്റ ചിത്രം",
    Grid: "Grid", Carousel: "Carousel", "Sticky gallery": "മുകളിൽ നിലനിർത്തുന്ന gallery",
    "Header center": "Header നടുക്ക്", "Header right": "Header വലത്", "Mobile header": "Mobile header", Footer: "Footer",
    "Announcement bar": "അറിയിപ്പ് ബാർ", "Hero slider": "പ്രധാന banner slider", "Hero banner": "പ്രധാന banner",
    "Shop by category": "വിഭാഗം അനുസരിച്ച് ഷോപ്പ്", "Featured products": "പ്രധാന products", "New arrivals": "പുതിയ വരവുകൾ",
    "Trending now": "ഇപ്പോൾ trending", "Best sellers": "ഏറ്റവും വിറ്റത്", Collections: "ശേഖരങ്ങൾ", Brands: "ബ്രാൻഡുകൾ",
    "Customer reviews": "ഉപഭോക്തൃ അഭിപ്രായങ്ങൾ", "Instagram feed": "Instagram feed", Newsletter: "Newsletter",
    "Promotional banner": "പ്രമോഷൻ banner", FAQ: "പതിവ് ചോദ്യങ്ങൾ", "Video banner": "Video banner", "Image gallery": "ചിത്രശേഖരം",
    "Countdown banner": "Countdown banner", "Recently viewed": "സമീപകാലത്ത് കണ്ടത്", "Recommended products": "ശുപാർശ ചെയ്യുന്ന products",
    "Flash sale": "Flash sale", "Trust bar": "വിശ്വാസ വിവരങ്ങൾ", "Product collection": "Product ശേഖരം",
    "On page load": "Page തുറക്കുമ്പോൾ", "On scroll": "Scroll ചെയ്യുമ്പോൾ", "On exit intent": "പുറത്തുകടക്കുമ്പോൾ",
    "After delay": "കുറച്ച് സമയം കഴിഞ്ഞ്", "On click": "Click ചെയ്യുമ്പോൾ", "Once per session": "ഓരോ session-ലും ഒരിക്കൽ",
    "Once per day": "ദിവസത്തിൽ ഒരിക്കൽ", "Every page load": "ഓരോ page തുറക്കുമ്പോഴും",
  };
  const actionTitles = {
    product_create: "Product സൃഷ്ടിക്കുക", product_update: "Product തിരുത്തുക", homepage_section_create: "Homepage വിഭാഗം ചേർക്കുക",
    homepage_section_update: "Homepage വിഭാഗം തിരുത്തുക", homepage_section_delete: "Homepage വിഭാഗം നീക്കുക",
    theme_update: "Website രൂപം തിരുത്തുക", content_page_create: "Page സൃഷ്ടിക്കുക", content_page_update: "Page തിരുത്തുക",
    banner_create: "Banner ചേർക്കുക", banner_update: "Banner തിരുത്തുക", navigation_create: "Navigation ലിങ്ക് ചേർക്കുക",
    navigation_update: "Navigation ലിങ്ക് തിരുത്തുക", announcement_update: "അറിയിപ്പ് തിരുത്തുക", blog_post_create: "Blog post ചേർക്കുക",
    blog_post_update: "Blog post തിരുത്തുക", faq_item_create: "FAQ ചേർക്കുക", faq_item_update: "FAQ തിരുത്തുക",
    category_create: "വിഭാഗം സൃഷ്ടിക്കുക", category_update: "വിഭാഗം തിരുത്തുക", popup_create: "Popup സൃഷ്ടിക്കുക", popup_update: "Popup തിരുത്തുക",
    website_settings_update: "Website ക്രമീകരണങ്ങൾ തിരുത്തുക", collection_create: "ശേഖരം സൃഷ്ടിക്കുക", collection_update: "ശേഖരം തിരുത്തുക",
  };
  const serverMessages = {
    "Local Ollama is unavailable. Start Ollama, confirm its URL, and pull the configured model.": "Local Ollama-യുമായി ബന്ധപ്പെടാനായില്ല. Ollama പ്രവർത്തിക്കുന്നുണ്ടോ, model ഇൻസ്റ്റാൾ ചെയ്തിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.",
    "Local Ollama returned an invalid response.": "Local Ollama-യിൽ നിന്ന് ശരിയായ മറുപടി ലഭിച്ചില്ല.",
    "Cloud Gemini is not configured. Add GEMINI_API_KEY to the server environment.": "Cloud Gemini സജ്ജീകരിച്ചിട്ടില്ല. Server-ൽ GEMINI_API_KEY ചേർക്കുക.",
    "Cloud Gemini rejected the API key or its permissions. Check the server secret.": "Gemini API key അല്ലെങ്കിൽ അതിന്റെ അനുമതി ശരിയല്ല. Server secret പരിശോധിക്കുക.",
    "Cloud Gemini rejected the request. Check the model setting and server logs.": "Cloud Gemini അഭ്യർത്ഥന സ്വീകരിച്ചില്ല. Model ക്രമീകരണവും server ലോഗുകളും പരിശോധിക്കുക.",
    "The configured Cloud Gemini model is unavailable. Update SYAFRA_AGENT_GEMINI_MODEL to a supported model.": "ക്രമീകരിച്ച Cloud Gemini model ലഭ്യമല്ല. SYAFRA_AGENT_GEMINI_MODEL-ൽ പിന്തുണയുള്ള model നൽകുക.",
    "Cloud Gemini is temporarily unavailable or overloaded. Wait briefly and try again.": "Cloud Gemini ഇപ്പോൾ താൽക്കാലികമായി ലഭ്യമല്ല. അൽപസമയം കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കുക.",
    "Could not connect to Cloud Gemini. Check the server's internet connection.": "Cloud Gemini-യുമായി ബന്ധപ്പെടാനായില്ല. Server-ന്റെ internet ബന്ധം പരിശോധിക്കുക.",
    "Cloud Gemini returned an invalid response.": "Cloud Gemini-യിൽ നിന്ന് ശരിയായ മറുപടി ലഭിച്ചില്ല.",
    "The preview could not be prepared. Try again or simplify the request.": "Preview തയ്യാറാക്കാനായില്ല. വീണ്ടും ശ്രമിക്കുകയോ നിർദ്ദേശം ലളിതമാക്കുകയോ ചെയ്യുക.",
    "Review the preview and explicitly confirm before applying changes.": "മാറ്റങ്ങൾ നടപ്പാക്കുന്നതിന് മുമ്പ് preview പരിശോധിച്ച് സ്ഥിരീകരിക്കുക.",
    "The preview data is invalid. Generate it again.": "Preview വിവരങ്ങൾ ശരിയല്ല. വീണ്ടും തയ്യാറാക്കുക.",
    "This preview has already been applied.": "ഈ preview-യിലെ മാറ്റങ്ങൾ ഇതിനകം നടപ്പാക്കിയിട്ടുണ്ട്.",
    "This preview expired. Generate a fresh preview before applying it.": "ഈ preview കാലഹരണപ്പെട്ടു. മാറ്റങ്ങൾ നടപ്പാക്കുന്നതിന് മുമ്പ് പുതിയത് തയ്യാറാക്കുക.",
    "The assistant needs more information before it can prepare changes.": "മാറ്റങ്ങൾ തയ്യാറാക്കുന്നതിന് മുമ്പ് assistant-ന് കൂടുതൽ വിവരങ്ങൾ വേണം.",
    "No website changes were drafted.": "Website-ൽ മാറ്റങ്ങളൊന്നും തയ്യാറാക്കിയിട്ടില്ല.",
  };

  function fieldLabel(definition) {
    return fieldLabels[definition.name] || definition.label;
  }

  function choiceLabel(label) {
    return choiceLabels[label] || label;
  }

  function localizeMessage(message) {
    if (serverMessages[message]) return serverMessages[message];
    if (message.startsWith("Cloud Gemini's current quota")) return "Cloud Gemini-യുടെ നിലവിലെ സൗജന്യ quota തീർന്നു. പിന്നീട് വീണ്ടും ശ്രമിക്കുക.";
    if (message.startsWith("Cloud Gemini took too long")) return "Cloud Gemini മറുപടി നൽകാൻ കൂടുതൽ സമയം എടുത്തു. കുറച്ച് അല്ലെങ്കിൽ ചെറിയ ചിത്രങ്ങൾ ഉപയോഗിക്കുക.";
    if (message.startsWith("The local AI model took too long")) return "AI model മറുപടി നൽകാൻ കൂടുതൽ സമയം എടുത്തു. ചെറിയ prompt അല്ലെങ്കിൽ ചെറിയ ചിത്രങ്ങൾ ഉപയോഗിച്ച് വീണ്ടും ശ്രമിക്കുക.";
    if (message.startsWith("Upload no more than ")) return "ഒരേസമയം പരമാവധി 10 ചിത്രങ്ങൾ മാത്രം upload ചെയ്യുക.";
    if (message.includes("exceeds the 8 MB image limit")) return "ഓരോ ചിത്രവും 8 MB-ൽ താഴെയായിരിക്കണം.";
    if (message.includes("could not be prepared") || message.includes("is not a valid image")) return "ചിത്രം തയ്യാറാക്കാനായില്ല. JPG, PNG അല്ലെങ്കിൽ WebP ചിത്രം ഉപയോഗിച്ച് വീണ്ടും ശ്രമിക്കുക.";
    if (message.includes("combined image upload must stay under 20 MB")) return "എല്ലാ ചിത്രങ്ങളുടെയും മൊത്തം വലുപ്പം 20 MB-യ്ക്കുള്ളിൽ ആയിരിക്കണം.";
    if (message.includes("too large to analyze together")) return "ഈ ചിത്രങ്ങൾ ഒരുമിച്ച് AI-ക്ക് വിശകലനം ചെയ്യാനാകില്ല. കുറച്ച് അല്ലെങ്കിൽ ചെറിയ ചിത്രങ്ങൾ upload ചെയ്ത് നോക്കുക.";
    return message;
  }

  let history = [];
  let currentDraft = null;
  let busy = false;

  function setStatus(message, kind) {
    liveStatus.textContent = message || "";
    liveStatus.classList.toggle("is-error", kind === "error");
    liveStatus.classList.toggle("is-success", kind === "success");
  }

  function appendMessage(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `agent-message ${role === "user" ? "agent-message-user" : "agent-message-assistant"}`;
    if (role !== "user") {
      const avatar = document.createElement("span");
      avatar.className = "agent-message-avatar";
      avatar.setAttribute("aria-hidden", "true");
      avatar.textContent = "S";
      bubble.appendChild(avatar);
    }
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    bubble.appendChild(paragraph);
    conversation.appendChild(bubble);
    conversation.scrollTop = conversation.scrollHeight;
  }

  function updateUploadPreview() {
    const files = Array.from(imageInput.files || []);
    uploadPreview.replaceChildren();
    uploadPreview.hidden = files.length === 0;
    uploadCount.textContent = files.length ? `${files.length} ചിത്രം തിരഞ്ഞെടുത്തു` : "പരമാവധി 10 ചിത്രങ്ങൾ";
    for (const file of files) {
      const image = document.createElement("img");
      image.className = "agent-upload-thumb";
      image.alt = file.name;
      image.src = URL.createObjectURL(file);
      image.addEventListener("load", () => URL.revokeObjectURL(image.src), { once: true });
      uploadPreview.appendChild(image);
    }
  }

  function showWorking(isWorking) {
    busy = isWorking;
    submitButton.disabled = isWorking;
    submitButton.querySelector("span:first-child").textContent = isWorking ? "തയ്യാറാക്കുന്നു…" : "Preview തയ്യാറാക്കുക";
    if (isWorking) setStatus("സ്റ്റോർ പരിശോധിച്ച് draft തയ്യാറാക്കുന്നു. ഇപ്പോൾ മാറ്റങ്ങളൊന്നും നടപ്പാക്കില്ല.");
  }

  async function postForm(url, formData) {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrfToken, Accept: "application/json" },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(localizeMessage(data.error || `അഭ്യർത്ഥന പരാജയപ്പെട്ടു (${response.status}). Admin session കാലഹരണപ്പെട്ടെങ്കിൽ പേജ് refresh ചെയ്യുക.`));
    }
    return data;
  }

  async function cancelDraft() {
    if (!currentDraft || !currentDraft.proposal_id) return;
    const data = new FormData();
    data.set("proposal_id", currentDraft.proposal_id);
    try {
      await postForm(app.dataset.cancelUrl, data);
    } catch (error) {
      setStatus(error.message, "error");
    }
    currentDraft = null;
    previewPanel.hidden = true;
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === "") return "നൽകിയിട്ടില്ല";
    if (typeof value === "boolean") return value ? "അതെ" : "ഇല്ല";
    return String(value);
  }

  function makeFieldControl(actionIndex, action, definition, categories, selectionChoices) {
    const wrapper = document.createElement("div");
    wrapper.className = "agent-field";
    const wide = definition.type === "textarea" || definition.name === "category_id";
    if (wide) wrapper.classList.add("agent-field-wide");
    const value = action.values[definition.name];
    const label = document.createElement("label");
    label.className = "agent-field-label";
    label.htmlFor = `agent-field-${actionIndex}-${definition.name}`;
    label.textContent = fieldLabel(definition);
    wrapper.appendChild(label);

    let control;
    if (definition.type === "boolean") {
      const row = document.createElement("label");
      row.className = "agent-field-boolean";
      control = document.createElement("input");
      control.type = "checkbox";
      control.checked = value === true;
      control.dataset.actionIndex = String(actionIndex);
      control.dataset.field = definition.name;
      control.id = label.htmlFor;
      row.append(control, document.createTextNode("പ്രവർത്തനക്ഷമം"));
      wrapper.appendChild(row);
    } else if (definition.type === "select" || ["category_id", "author_id", "parent_id", "section_id", "lookbook_id", "product_id", "collection_id", "testimonial_id"].includes(definition.name)) {
      control = document.createElement("select");
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "ഒരു ഓപ്ഷൻ തിരഞ്ഞെടുക്കുക";
      control.appendChild(empty);
      let choices = (definition.choices || []).map((choice) => [String(choice[0]), choiceLabel(choice[1])]);
      if (definition.name === "category_id") {
        const rows = action.kind.startsWith("blog_post")
          ? selectionChoices.blog_categories || []
          : action.kind.startsWith("faq_item")
            ? selectionChoices.faq_categories || []
            : categories;
        choices = rows.map((item) => [String(item.id), item.name]);
        empty.textContent = action.kind.startsWith("faq_item") || action.kind.startsWith("product_")
          ? "ഒരു വിഭാഗം തിരഞ്ഞെടുക്കുക"
          : "വിഭാഗമില്ല";
      } else if (definition.name === "author_id") {
        choices = (selectionChoices.blog_authors || []).map((item) => [String(item.id), item.name]);
        empty.textContent = "രചയിതാവില്ല";
      } else if (definition.name === "parent_id") {
        const navigationItems = selectionChoices.navigation_items || [];
        const disallowed = new Set(action.record_id ? [action.record_id] : []);
        let changed = true;
        while (changed) {
          changed = false;
          for (const item of navigationItems) {
            if (disallowed.has(item.parent_id) && !disallowed.has(item.id)) {
              disallowed.add(item.id);
              changed = true;
            }
          }
        }
        choices = navigationItems.filter((item) => !disallowed.has(item.id))
          .map((item) => [String(item.id), item.label]);
        empty.textContent = "പ്രധാന navigation ഇനം";
      } else if (definition.name === "section_id") {
        choices = (selectionChoices.homepage_sections || []).map((item) => [
          String(item.id),
          `${item.section_type}${item.title ? ` — ${item.title}` : ""}`,
        ]);
        empty.textContent = "ഒരു homepage വിഭാഗം തിരഞ്ഞെടുക്കുക";
      } else if (definition.name === "lookbook_id") {
        choices = (selectionChoices.lookbooks || []).map((item) => [String(item.id), item.title]);
        empty.textContent = "ഒരു lookbook തിരഞ്ഞെടുക്കുക";
      } else if (definition.name === "product_id") {
        choices = (selectionChoices.products || []).map((item) => [String(item.id), item.name]);
        empty.textContent = "ബന്ധിപ്പിച്ച product ഇല്ല";
      } else if (definition.name === "collection_id") {
        choices = (selectionChoices.collections || []).map((item) => [String(item.id), item.name]);
        empty.textContent = "ഒരു collection തിരഞ്ഞെടുക്കുക";
      } else if (definition.name === "testimonial_id") {
        choices = (selectionChoices.testimonials || []).map((item) => [String(item.id), item.name]);
        empty.textContent = "ഒരു testimonial തിരഞ്ഞെടുക്കുക";
      }
      for (const [choiceValue, localizedChoiceLabel] of choices) {
        const option = document.createElement("option");
        option.value = choiceValue;
        option.textContent = localizedChoiceLabel;
        control.appendChild(option);
      }
      control.value = value === null || value === undefined ? "" : String(value);
      control.dataset.actionIndex = String(actionIndex);
      control.dataset.field = definition.name;
      control.id = label.htmlFor;
      wrapper.appendChild(control);
    } else if (definition.type === "color") {
      const row = document.createElement("div");
      row.className = "agent-field-color-row";
      control = document.createElement("input");
      control.type = "color";
      control.value = /^#[0-9a-f]{6}$/i.test(String(value || "")) ? value : "#ffffff";
      control.dataset.actionIndex = String(actionIndex);
      control.dataset.field = definition.name;
      control.id = label.htmlFor;
      const sample = document.createElement("span");
      sample.className = "agent-change-before";
      sample.textContent = value ? `മുമ്പ്: ${displayValue(action.before && action.before[definition.name])}` : "ഒരു നിറം തിരഞ്ഞെടുക്കുക";
      row.append(control, sample);
      wrapper.appendChild(row);
    } else if (definition.type === "textarea" || definition.type === "sizes") {
      control = document.createElement("textarea");
      control.rows = definition.name === "content" || definition.type === "sizes" ? 5 : 3;
      if (definition.type === "sizes") control.placeholder = "S: 2\nM: 3";
      control.value = value === null || value === undefined ? "" : String(value);
      control.dataset.actionIndex = String(actionIndex);
      control.dataset.field = definition.name;
      control.id = label.htmlFor;
      wrapper.appendChild(control);
    } else {
      control = document.createElement("input");
      control.type = definition.type === "integer" ? "number" : definition.type === "decimal" ? "number" : "text";
      if (definition.type === "integer") control.step = "1";
      if (definition.type === "decimal") control.step = "0.01";
      if (action.kind.startsWith("product_") && definition.name === "price") control.min = "0";
      if (definition.name === "products_per_page") {
        control.min = "1";
        control.max = "100";
      }
      if (definition.name === "font_size_scale") {
        control.min = "0.8";
        control.max = "1.5";
        control.step = "0.1";
      }
      if (definition.name === "line_height") {
        control.min = "0.8";
        control.max = "3.0";
        control.step = "0.1";
      }
      if (["overlay_opacity", "image_position_x", "image_position_y", "scroll_percent"].includes(definition.name)) {
        control.min = "0";
        control.max = "100";
      }
      if (definition.name === "delay_seconds") control.min = "0";
      if (definition.name === "stock" || definition.name === "footer_columns" || definition.name === "display_order") control.min = "0";
      control.value = value === null || value === undefined ? "" : String(value);
      if (action.kind === "product_create" && definition.name === "price") {
        control.placeholder = "നിങ്ങൾ നിശ്ചയിച്ച വില നൽകുക";
        control.required = true;
      }
      if (action.kind === "product_create" && definition.name === "sizes") {
        control.placeholder = "S: 2\nM: 3";
        control.required = true;
      }
      control.dataset.actionIndex = String(actionIndex);
      control.dataset.field = definition.name;
      control.id = label.htmlFor;
      wrapper.appendChild(control);
    }

    if (action.kind === "product_create" && definition.name === "price") {
      const help = document.createElement("span");
      help.className = "agent-field-help";
      help.textContent = "നിങ്ങൾ നൽകുന്ന വില product photo-യിലും listing-ലും ചേർക്കും.";
      wrapper.appendChild(help);
    }
    if (action.kind === "product_create" && definition.name === "sizes") {
      const help = document.createElement("span");
      help.className = "agent-field-help";
      help.textContent = "നിർബന്ധമാണ്. ഓരോ സൈസും വേറെ വരിയിൽ SIZE: quantity എന്ന രീതിയിൽ നൽകുക. മൊത്തം stock താനേ കണക്കാക്കും.";
      wrapper.appendChild(help);
    }

    if (action.before && Object.prototype.hasOwnProperty.call(action.before, definition.name)) {
      const before = document.createElement("span");
      before.className = "agent-change-before";
      before.textContent = `നിലവിൽ: ${displayValue(action.before[definition.name])}`;
      wrapper.appendChild(before);
    }
    return wrapper;
  }

  function fieldsForAction(action) {
    const definitions = fieldDefinitions[action.kind] || [];
    if (action.kind.endsWith("_create")) {
      return definitions.filter((definition) => (definition.name !== "new_category_name" || canCreateCategory) && !(action.kind === "product_create" && definition.name === "stock"));
    }
    return definitions.filter((definition) => {
      if (definition.name === "new_category_name" && !canCreateCategory) return false;
      if (action.kind === "product_create") return true;
      if (action.kind.startsWith("product_") && ["category_id", "new_category_name"].includes(definition.name)) return true;
      return Object.prototype.hasOwnProperty.call(action.values, definition.name);
    });
  }

  function createImageThumb(attachment, actionIndex, imageIndex) {
    const wrap = document.createElement("div");
    wrap.className = "agent-image-wrap";
    const image = document.createElement("img");
    image.className = "agent-image-thumb";
    image.src = attachment.url;
    image.alt = attachment.name;
    image.dataset.imageIndex = String(imageIndex);
    wrap.appendChild(image);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "agent-image-remove";
    remove.title = "ഈ ചിത്രം draft-ിൽ നിന്ന് നീക്കുക";
    remove.setAttribute("aria-label", `${attachment.name} ചിത്രം draft-ിൽ നിന്ന് നീക്കുക`);
    remove.dataset.removeImage = String(imageIndex);
    remove.dataset.actionIndex = String(actionIndex);
    remove.textContent = "×";
    wrap.appendChild(remove);
    if (attachment.edit_url) {
      const editForm = document.createElement("form");
      editForm.className = "agent-photo-edit-form";
      editForm.dataset.photoEdit = "true";
      editForm.dataset.editUrl = attachment.edit_url;
      editForm.dataset.imageIndex = String(imageIndex);
      const editPrompt = document.createElement("input");
      editPrompt.type = "text";
      editPrompt.name = "prompt";
      editPrompt.maxLength = 500;
      editPrompt.placeholder = "തിരുത്തേണ്ടത് നിർദ്ദേശിക്കുക";
      editPrompt.setAttribute("aria-label", `${attachment.name} ചിത്രം നിർദ്ദേശം നൽകി തിരുത്തുക`);
      editPrompt.required = true;
      const editButton = document.createElement("button");
      editButton.type = "submit";
      editButton.textContent = "തിരുത്തുക";
      const editStatus = document.createElement("span");
      editStatus.className = "agent-photo-edit-status";
      editStatus.setAttribute("role", "status");
      editForm.append(editPrompt, editButton, editStatus);
      wrap.appendChild(editForm);
    }
    return wrap;
  }

  function setThemePreview(actions) {
    const themeAction = actions.find((action) => action.kind === "theme_update");
    if (!themeAction) {
      visualPreview.hidden = true;
      visualPreview.replaceChildren();
      return;
    }
    visualPreview.hidden = false;
    visualPreview.replaceChildren();
    const values = themeAction.values;
    const before = themeAction.before || {};
    const combined = { ...before, ...values };
    const cssColors = {
      "--preview-primary": combined.primary_color,
      "--preview-secondary": combined.secondary_color,
      "--preview-accent": combined.accent_color,
      "--preview-background": combined.background_color,
      "--preview-text": combined.text_color,
      "--preview-muted": combined.muted_text_color,
    };
    for (const [property, color] of Object.entries(cssColors)) {
      if (/^#[0-9a-f]{6}$/i.test(String(color || ""))) visualPreview.style.setProperty(property, color);
    }
    const nav = document.createElement("div");
    nav.className = "agent-store-preview-nav";
    const store = document.createElement("strong");
    store.textContent = combined.store_name || "SYAFRA";
    const links = document.createElement("span");
    links.textContent = "ഷോപ്പ് · ഞങ്ങളെക്കുറിച്ച് · കാർട്ട്";
    nav.append(store, links);
    const copy = document.createElement("div");
    copy.className = "agent-store-preview-copy";
    const eyebrow = document.createElement("span");
    eyebrow.textContent = "സ്റ്റോർഫ്രണ്ട് രൂപത്തിന്റെ preview";
    const title = document.createElement("h3");
    title.textContent = combined.tagline || "നിങ്ങൾക്കായി തിരഞ്ഞെടുത്ത വസ്ത്രങ്ങൾ";
    const paragraph = document.createElement("p");
    paragraph.textContent = `Header: ${combined.header_style || "classic"} · Product grid: ${combined.product_grid_layout || "4cols"} · Layout: ${combined.layout_style || "full_width"}`;
    const button = document.createElement("button");
    button.className = "agent-store-preview-button";
    button.type = "button";
    button.textContent = "ശേഖരം കാണുക";
    copy.append(eyebrow, title, paragraph, button);
    visualPreview.append(nav, copy);
  }

  function syncActionPreviews(actions) {
    actions.forEach((action, index) => {
      const card = previewActions.querySelector(`[data-action-card="${index}"]`);
      if (!card) return;
      if (action.kind.startsWith("product_")) {
        const productPreview = card.querySelector("[data-product-preview]");
        const name = productPreview && productPreview.querySelector(".agent-product-preview-copy strong");
        const price = productPreview && productPreview.querySelector(".agent-product-preview-copy > span");
        const photoPrice = productPreview && productPreview.querySelector("[data-product-price-callout]");
        const photoArrow = productPreview && productPreview.querySelector("[data-product-price-arrow]");
        const amount = action.values.price || (action.before && action.before.price);
        if (name) name.textContent = action.values.name || (action.before && action.before.name) || "Product-ന്റെ പേര് നൽകണം";
        if (price) price.textContent = amount ? `₹${amount}/-` : "സ്ഥിരീകരിക്കുന്നതിന് മുമ്പ് വില നൽകുക";
        if (photoPrice) {
          photoPrice.textContent = amount ? `₹${amount}/-` : "";
          photoPrice.hidden = !amount;
        }
        if (photoArrow) photoArrow.hidden = !amount;
      }
      const description = card.querySelector("[data-action-description]");
      if (description && action.kind === "website_settings_update" && action.values.maintenance_mode === true) {
        description.textContent = "ഇത് storefront-നെ maintenance mode-ലാക്കും.";
        if (!card.querySelector(".agent-warning")) {
          const warning = document.createElement("p");
          warning.className = "agent-warning";
          warning.textContent = "സ്ഥിരീകരിച്ചാൽ സന്ദർശകർക്ക് maintenance page കാണിക്കും.";
          card.insertBefore(warning, card.querySelector(".agent-action-fields"));
        }
      } else if (description && action.kind === "website_settings_update") {
        description.textContent = "ഈ വിവരങ്ങൾ Syafra website-ൽ save ചെയ്യും.";
        card.querySelector(".agent-warning")?.remove();
      }
    });
    setThemePreview(actions);
  }

  function renderPreview(data) {
    currentDraft = data;
    previewPanel.hidden = false;
    previewPanel.querySelector(".agent-confirm-area").hidden = false;
    previewPanel.querySelector(".agent-result-list")?.remove();
    previewReply.textContent = data.reply || "നിർദ്ദേശിച്ച മാറ്റങ്ങൾ താഴെ പരിശോധിക്കുക.";
    expiryLabel.textContent = "Draft 20 മിനിറ്റിനുള്ളിൽ കാലഹരണപ്പെടും";
    previewActions.replaceChildren();

    data.actions.forEach((action, actionIndex) => {
      const card = document.createElement("article");
      card.className = "agent-action-card";
      card.dataset.actionCard = String(actionIndex);
      const heading = document.createElement("div");
      heading.className = "agent-action-heading";
      const title = document.createElement("h3");
      title.textContent = actionTitles[action.kind] || action.summary || action.kind.replaceAll("_", " ");
      const description = document.createElement("p");
      description.dataset.actionDescription = "true";
      const isDelete = action.kind.endsWith("_delete");
      description.textContent = isDelete
        ? "സ്ഥിരീകരിച്ചാൽ ഈ record ശാശ്വതമായി നീക്കം ചെയ്യും."
        : action.kind.startsWith("product_")
        ? action.kind === "product_create" ? "സ്ഥിരീകരിച്ച പുതിയ product live catalog-ൽ ചേർക്കും." : `Product #${action.record_id} തിരുത്തും.`
        : action.kind === "website_settings_update" && action.values.maintenance_mode === true
          ? "ഇത് storefront-നെ maintenance mode-ലാക്കും."
          : "ഈ വിവരങ്ങൾ Syafra website-ൽ save ചെയ്യും.";
      heading.append(title, description);
      card.appendChild(heading);

      if (isDelete) {
        const warning = document.createElement("p");
        warning.className = "agent-warning";
        warning.textContent = "ശാശ്വതമായി നീക്കം ചെയ്യും: സ്ഥിരീകരിക്കുന്നതിന് മുമ്പ് ഈ record-ും ബന്ധിപ്പിച്ച ഇനങ്ങളും പരിശോധിക്കുക.";
        card.appendChild(warning);

        const details = document.createElement("details");
        details.className = "agent-delete-details";
        const summary = document.createElement("summary");
        summary.textContent = "Record-ിന്റെയും ബന്ധിപ്പിച്ച ഇനങ്ങളുടെയും വിവരങ്ങൾ";
        details.appendChild(summary);
        const list = document.createElement("ul");
        const record = document.createElement("li");
        record.textContent = `Record: ${action.before?.record || action.summary || action.kind}`;
        list.appendChild(record);
        for (const related of action.before?.related_records || []) {
          const item = document.createElement("li");
          const effect = related.on_delete === "CASCADE" ? "ഇതും നീക്കം ചെയ്യും" : "ഇതിനെ ബാധിച്ചേക്കാം";
          item.textContent = `${related.count} ${related.type} — ${effect}`;
          list.appendChild(item);
        }
        details.appendChild(list);
        card.appendChild(details);
      }

      if (action.kind === "website_settings_update" && action.values.maintenance_mode === true) {
        const warning = document.createElement("p");
        warning.className = "agent-warning";
        warning.textContent = "സ്ഥിരീകരിച്ചാൽ സന്ദർശകർക്ക് maintenance page കാണിക്കും.";
        card.appendChild(warning);
      }

      const fields = document.createElement("div");
      fields.className = "agent-action-fields";
      const fieldList = fieldsForAction(action);
      const categories = data.categories || [];
      for (const definition of fieldList) {
        const field = makeFieldControl(actionIndex, action, definition, categories, data.choices || {});
        fields.appendChild(field);
      }
      card.appendChild(fields);

      if (action.kind === "product_update") {
        const replaceLabel = document.createElement("label");
        replaceLabel.className = "agent-replace-images";
        const replace = document.createElement("input");
        replace.type = "checkbox";
        replace.checked = action.replace_images === true;
        replace.dataset.actionIndex = String(actionIndex);
        replace.dataset.replaceImages = "true";
        const oldImageCount = Number(action.before && action.before.existing_image_count) || 0;
        const replaceText = document.createElement("span");
        replaceText.textContent = `നിലവിലെ ${oldImageCount} product photo-കൾ തിരഞ്ഞെടുത്ത ചിത്രങ്ങൾ ഉപയോഗിച്ച് മാറ്റുക`;
        replaceLabel.append(replace, replaceText);
        card.appendChild(replaceLabel);
      }

      const images = document.createElement("div");
      images.className = "agent-action-images";
      for (const imageIndex of action.image_indices || []) {
        const attachment = (data.attachments || []).find((item) => item.index === imageIndex);
        if (attachment) images.appendChild(createImageThumb(attachment, actionIndex, imageIndex));
      }
      if (images.childElementCount) {
        card.appendChild(images);
        if (action.kind.startsWith("product_")) {
          const photoNote = document.createElement("p");
          photoNote.className = "agent-photo-note";
          photoNote.textContent = "Brightness, contrast, warm/cool tone, color, sharpness, black-and-white എന്നിവ prompt നൽകി മാറ്റാം. Local Python edit-ന് ചിത്രത്തിലെ വസ്തുക്കൾ ചേർക്കാനോ നീക്കാനോ കഴിയില്ല.";
          card.appendChild(photoNote);
        }
      }

      if (action.kind.startsWith("product_")) {
        const productPreview = document.createElement("div");
        productPreview.className = "agent-product-preview";
        productPreview.dataset.productPreview = "true";
        const firstIndex = (action.image_indices || [])[0];
        const imageData = (data.attachments || []).find((item) => item.index === firstIndex);
        if (imageData) {
          const photoFrame = document.createElement("div");
          photoFrame.className = "agent-product-photo-frame";
          const image = document.createElement("img");
          image.className = "agent-image-thumb";
          image.src = imageData.url;
          image.alt = imageData.name;
          image.dataset.imageIndex = String(imageData.index);
          photoFrame.appendChild(image);
          const photoPrice = document.createElement("span");
          photoPrice.className = "agent-product-photo-price";
          photoPrice.dataset.productPriceCallout = "true";
          photoPrice.setAttribute("aria-label", "Admin നൽകിയ product photo വില");
          const initialPrice = action.values.price || (action.before && action.before.price);
          photoPrice.textContent = initialPrice ? `₹${initialPrice}/-` : "";
          photoPrice.hidden = !initialPrice;
          photoFrame.appendChild(photoPrice);
          const arrow = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          arrow.setAttribute("viewBox", "0 0 100 100");
          arrow.setAttribute("aria-hidden", "true");
          arrow.classList.add("agent-product-photo-arrow");
          arrow.dataset.productPriceArrow = "true";
          arrow.hidden = !initialPrice;
          const curve = document.createElementNS("http://www.w3.org/2000/svg", "path");
          curve.setAttribute("d", "M78 4 C84 37 59 57 31 82 M20 68 L31 82 L46 77");
          curve.setAttribute("fill", "none");
          curve.setAttribute("stroke", "currentColor");
          curve.setAttribute("stroke-linecap", "round");
          curve.setAttribute("stroke-linejoin", "round");
          curve.setAttribute("stroke-width", "4");
          arrow.appendChild(curve);
          photoFrame.appendChild(arrow);
          productPreview.appendChild(photoFrame);
        }
        const copy = document.createElement("div");
        copy.className = "agent-product-preview-copy";
        const name = document.createElement("strong");
        name.textContent = action.values.name || (action.before && action.before.name) || "Product-ന്റെ പേര് നൽകണം";
        const price = document.createElement("span");
        price.textContent = action.values.price ? `₹${action.values.price}` : (action.before && action.before.price ? `₹${action.before.price}` : "സ്ഥിരീകരിക്കുന്നതിന് മുമ്പ് വില നൽകുക");
        copy.append(name, price);
        productPreview.appendChild(copy);
        card.appendChild(productPreview);
      }

      previewActions.appendChild(card);
    });
    setThemePreview(data.actions);
    confirmCheckbox.checked = false;
    updateConfirmState();
    previewPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function readControlValue(control, definition) {
    if (definition.type === "boolean") return control.checked;
    if (control.value === "") return null;
    if (definition.type === "integer" || definition.name === "category_id") return Number.parseInt(control.value, 10);
    if (definition.type === "decimal") return control.value;
    return control.value;
  }

  function readDraftActions() {
    if (!currentDraft) return [];
    const actions = structuredClone(currentDraft.actions);
    previewActions.querySelectorAll("[data-field]").forEach((control) => {
      const index = Number(control.dataset.actionIndex);
      const name = control.dataset.field;
      const definition = (fieldDefinitions[actions[index].kind] || []).find((item) => item.name === name);
      if (!definition) return;
      const value = readControlValue(control, definition);
      if (value === null) delete actions[index].values[name];
      else actions[index].values[name] = value;
    });
    actions.forEach((action) => {
      if (action.kind !== "product_create") return;
      const parsedSizes = parseSizeStock(action.values.sizes);
      if (!parsedSizes.error && parsedSizes.entries.length) action.values.stock = parsedSizes.total;
      else delete action.values.stock;
    });
    previewActions.querySelectorAll("[data-replace-images]").forEach((control) => {
      actions[Number(control.dataset.actionIndex)].replace_images = control.checked;
    });
    return actions;
  }

  function parseSizeStock(text) {
    const entries = [];
    const seen = new Set();
    let total = 0;
    const rows = String(text || "").split(/[\n,]+/).map((row) => row.trim()).filter(Boolean);
    for (const row of rows) {
      const match = row.match(/^(.{1,10}?)\s*[:=]\s*(\d+)$/);
      if (!match) return { error: "ഓരോ സൈസിനും `SIZE: quantity` എന്ന രൂപം ഉപയോഗിക്കുക. ഉദാ: M: 3." };
      const size = match[1].trim().toUpperCase();
      const key = size.toLowerCase();
      const stock = Number(match[2]);
      if (!size || size.length > 10) return { error: "ഓരോ സൈസും 1 മുതൽ 10 അക്ഷരങ്ങൾക്കുള്ളിലായിരിക്കണം." };
      if (seen.has(key)) return { error: `${size} size ഒന്നിലധികം തവണ നൽകിയിട്ടുണ്ട്.` };
      if (!Number.isSafeInteger(stock)) return { error: "Size stock പൂജ്യമോ അതിലധികമോ ഉള്ള പൂർണ്ണ സംഖ്യയായിരിക്കണം." };
      seen.add(key);
      total += stock;
      entries.push({ size, stock });
    }
    if (entries.length > 20) return { error: "20-ൽ കൂടുതൽ product sizes നൽകരുത്." };
    return { entries, total };
  }

  function checkRequired(actions) {
    const errors = [];
    actions.forEach((action, index) => {
      const values = action.values;
      if (action.kind === "product_create") {
        for (const [name, label] of [["name", "AI തയ്യാറാക്കിയ product പേര്"], ["brand", "AI തയ്യാറാക്കിയ brand"], ["condition", "AI വിലയിരുത്തിയ നില"], ["price", "വില"], ["sizes", "size stock വിവരങ്ങൾ"]]) {
          if (values[name] === null || values[name] === undefined || values[name] === "") errors.push(`Product ${index + 1}-ന് ${label} ചേർക്കുക.`);
        }
        if (!values.category_id && !String(values.new_category_name || "").trim()) errors.push(`Product ${index + 1}-ന് ഒരു വിഭാഗം തിരഞ്ഞെടുക്കുക.`);
        if (values.category_id && String(values.new_category_name || "").trim()) errors.push(`Product ${index + 1}-ന് നിലവിലുള്ളതോ പുതിയതോ ആയ ഒരു വിഭാഗം മാത്രം തിരഞ്ഞെടുക്കുക.`);
        if (values.price && Number(values.price) < 0) errors.push(`Product ${index + 1}-ന്റെ വില നെഗറ്റീവ് ആകരുത്.`);
        const parsedSizes = parseSizeStock(values.sizes);
        if (parsedSizes.error) errors.push(`Product ${index + 1}: ${parsedSizes.error}`);
        else if (!parsedSizes.entries.length || parsedSizes.total < 1) errors.push(`Product ${index + 1}-ന്റെ ഏതെങ്കിലും size-ൽ കുറഞ്ഞത് ഒരു stock എങ്കിലും നൽകുക.`);
      }
      if (action.kind === "content_page_create" && (!values.title || !values.slug)) errors.push("പുതിയ page-ന് തലക്കെട്ടും URL slug-ഉം നൽകുക.");
      if (action.kind === "banner_create" && !values.title) errors.push("പുതിയ banner-ന് തലക്കെട്ട് നൽകുക.");
      if (["category_create", "faq_category_create", "legal_page_create", "blog_post_create"].includes(action.kind)) {
        const titleField = action.kind === "category_create" || action.kind === "faq_category_create" ? "name" : "title";
        if (!values[titleField] || !values.slug) errors.push("പുതിയ page അല്ലെങ്കിൽ വിഭാഗത്തിന് പേരും URL slug-ഉം നൽകുക.");
      }
      if (action.kind === "faq_item_create" && (!values.category_id || !values.question || !values.answer)) errors.push("FAQ വിഭാഗം തിരഞ്ഞെടുത്ത് ചോദ്യവും ഉത്തരവും നൽകുക.");
      if (action.kind === "navigation_create" && !values.label) errors.push("Navigation ലിങ്കിന് ഒരു പേര് നൽകുക.");
      if (action.kind === "popup_create" && !values.title) errors.push("പ്രമോഷൻ popup-ന് തലക്കെട്ട് നൽകുക.");
      if (action.kind === "hero_slide_create" && !values.section_id) errors.push("Hero slide-നായി homepage വിഭാഗം തിരഞ്ഞെടുക്കുക.");
      if (action.kind === "brand_create" && (!values.name || !values.slug)) errors.push("Brand പേരും URL slug-ഉം നൽകുക.");
      if (action.kind === "shop_category_create" && (!values.section_id || !values.category_id)) errors.push("ഈ tile-നായി homepage വിഭാഗവും product category-യും തിരഞ്ഞെടുക്കുക.");
      if (action.kind === "trust_item_create" && (!values.section_id || !values.title)) errors.push("Homepage വിഭാഗം തിരഞ്ഞെടുത്ത് trust bar തലക്കെട്ട് നൽകുക.");
      if (action.kind === "footer_link_create" && (!values.section_id || !values.column_heading || !values.label || !values.url)) errors.push("Section, footer നിരയുടെ തലക്കെട്ട്, link പേര്, destination എന്നിവ പൂരിപ്പിക്കുക.");
      if (action.kind === "testimonial_create" && (!values.name || !values.review)) errors.push("ഉപഭോക്താവിന്റെ പേര്, അഭിപ്രായം എന്നിവ നൽകുക.");
      if (action.kind === "collection_create" && (!values.name || !values.slug)) errors.push("Collection പേരും URL slug-ഉം നൽകുക.");
      if (action.kind === "collection_product_create" && (!values.collection_id || !values.product_id)) errors.push("Collection-ഉം product-ഉം തിരഞ്ഞെടുക്കുക.");
      if (action.kind === "testimonial_extended_create" && !values.testimonial_id) errors.push("ഒരു testimonial തിരഞ്ഞെടുക്കുക.");
      if (action.kind === "lookbook_create" && (!values.title || !values.slug)) errors.push("Lookbook-ന് തലക്കെട്ടും URL slug-ഉം നൽകുക.");
      if (action.kind === "lookbook_item_create" && !values.lookbook_id) errors.push("ഈ ഇനത്തിനായി ഒരു lookbook തിരഞ്ഞെടുക്കുക.");
      if (action.kind === "product_update" && action.replace_images && !(action.image_indices || []).length) errors.push("പുതിയ ചിത്രം തിരഞ്ഞെടുക്കുക അല്ലെങ്കിൽ photo മാറ്റാനുള്ള ഓപ്ഷൻ ഒഴിവാക്കുക.");
      if (action.kind.startsWith("product_") && values.price !== undefined && values.price !== null && values.price !== "" && (!Number.isFinite(Number(values.price)) || Number(values.price) < 0)) errors.push("ശരിയായ പൂജ്യമോ അതിലധികമോ ഉള്ള വില നൽകുക.");
      if (action.kind.startsWith("product_") && values.stock !== undefined && values.stock !== null && values.stock !== "" && (!Number.isInteger(Number(values.stock)) || Number(values.stock) < 0)) errors.push("സ്റ്റോക്ക് പൂജ്യമോ അതിലധികമോ ഉള്ള പൂർണ്ണ സംഖ്യയായിരിക്കണം.");
      const bounds = {
        font_size_scale: [0.8, 1.5], line_height: [0.8, 3], footer_columns: [1, 6],
        products_per_page: [1, 100], overlay_opacity: [0, 100], image_position_x: [0, 100],
        image_position_y: [0, 100], delay_seconds: [0, 86400], scroll_percent: [0, 100],
      };
      for (const [name, [minimum, maximum]] of Object.entries(bounds)) {
        if (values[name] !== undefined && values[name] !== null && values[name] !== "") {
          const number = Number(values[name]);
          if (!Number.isFinite(number) || number < minimum || number > maximum) errors.push(`${fieldLabel({ name, label: name.replaceAll("_", " ") })} ${minimum} മുതൽ ${maximum} വരെയായിരിക്കണം.`);
        }
      }
    });
    return errors;
  }

  function updateConfirmState() {
    if (!currentDraft || !confirmButton) return;
    const actions = readDraftActions();
    const errors = checkRequired(actions);
    syncActionPreviews(actions);
    const accepted = confirmCheckbox.checked;
    confirmButton.disabled = !accepted || errors.length > 0 || busy;
    validationMessage.textContent = errors[0] || (accepted ? "സ്ഥിരീകരിക്കാൻ തയ്യാറാണ്." : "മാറ്റങ്ങൾ പരിശോധിച്ച ശേഷം ഈ box തിരഞ്ഞെടുക്കുക.");
    validationMessage.classList.toggle("is-error", errors.length > 0);
  }

  function renderResults(data) {
    const area = document.createElement("div");
    area.className = "agent-result-list";
    const heading = document.createElement("strong");
    heading.textContent = "സ്ഥിരീകരിച്ച് നടപ്പാക്കി";
    area.appendChild(heading);
    for (const item of data.applied || []) {
      const line = document.createElement("div");
      const text = document.createElement("span");
      text.textContent = `${item.label}: ${item.name}`;
      line.appendChild(text);
      if (item.admin_url) {
        const link = document.createElement("a");
        link.href = item.admin_url;
        link.textContent = "Admin-ൽ തുറക്കുക";
        line.appendChild(link);
      }
      if (item.url) {
        const link = document.createElement("a");
        link.href = item.url;
        link.textContent = "Product കാണുക";
        link.target = "_blank";
        link.rel = "noopener";
        line.appendChild(link);
      }
      area.appendChild(line);
    }
    previewPanel.querySelector(".agent-confirm-area").hidden = true;
    previewPanel.appendChild(area);
    currentDraft = null;
    imageInput.value = "";
    updateUploadPreview();
    setStatus("സ്ഥിരീകരിച്ച മാറ്റങ്ങൾ നടപ്പാക്കി.", "success");
  }

  imageInput.addEventListener("change", updateUploadPreview);
  confirmCheckbox.addEventListener("change", updateConfirmState);
  previewActions.addEventListener("input", updateConfirmState);
  previewActions.addEventListener("change", updateConfirmState);

  previewActions.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-image]");
    if (!button || !currentDraft) return;
    const action = currentDraft.actions[Number(button.dataset.actionIndex)];
    action.image_indices = action.image_indices.filter((imageIndex) => imageIndex !== Number(button.dataset.removeImage));
    renderPreview(currentDraft);
  });

  previewActions.addEventListener("submit", async (event) => {
    const editForm = event.target.closest("[data-photo-edit]");
    if (!editForm || !currentDraft || busy) return;
    event.preventDefault();
    const editPrompt = editForm.elements.prompt.value.trim();
    const editStatus = editForm.querySelector(".agent-photo-edit-status");
    if (!editPrompt) return;
    const attachment = currentDraft.attachments.find((item) => item.index === Number(editForm.dataset.imageIndex));
    if (!attachment) return;
    const data = new FormData();
    data.set("proposal_id", currentDraft.proposal_id);
    data.set("prompt", editPrompt);
    busy = true;
    editForm.querySelector("button").disabled = true;
    editStatus.textContent = "ഇവിടെത്തന്നെ തിരുത്തുന്നു…";
    updateConfirmState();
    try {
      const result = await postForm(editForm.dataset.editUrl, data);
      attachment.url = result.url;
      previewActions.querySelectorAll(`[data-image-index="${attachment.index}"]`).forEach((image) => {
        image.src = result.url;
      });
      editPrompt.value = "";
      editStatus.textContent = `മാറ്റം പ്രയോഗിച്ചു: ${result.summary}`;
      setStatus("Draft ചിത്രം തിരുത്തി. സ്ഥിരീകരിക്കുന്നതിന് മുമ്പ് പരിശോധിക്കുക.", "success");
    } catch (error) {
      editStatus.textContent = error.message;
      setStatus(error.message, "error");
    } finally {
      busy = false;
      editForm.querySelector("button").disabled = false;
      updateConfirmState();
    }
  });

  previewActions.addEventListener("change", (event) => {
    const control = event.target;
    if (control.dataset.field === "category_id") {
      const action = currentDraft.actions[Number(control.dataset.actionIndex)];
      const newCategory = previewActions.querySelector(`[data-action-index="${control.dataset.actionIndex}"][data-field="new_category_name"]`);
      if (control.value && newCategory) newCategory.value = "";
      if (action) updateConfirmState();
    }
    const newCategoryControl = control.dataset.field === "new_category_name" ? control : null;
    if (newCategoryControl && newCategoryControl.value.trim()) {
      const categoryControl = previewActions.querySelector(`[data-action-index="${newCategoryControl.dataset.actionIndex}"][data-field="category_id"]`);
      if (categoryControl) categoryControl.value = "";
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    await cancelDraft();
    const prompt = promptInput.value.trim();
    if (!prompt) return;
    const priorHistory = history.slice(-12);
    appendMessage("user", prompt);
    history.push({ role: "user", content: prompt });
    const data = new FormData();
    data.set("prompt", prompt);
    data.set("history", JSON.stringify(priorHistory));
    data.set("product_photo_mode", photoModeInput.value);
    for (const file of Array.from(imageInput.files || [])) data.append("images", file);
    showWorking(true);
    try {
      const result = await postForm(app.dataset.planUrl, data);
      const answer = [result.reply, result.question].filter(Boolean).join("\n\n");
      if (answer) {
        appendMessage("assistant", answer);
        history.push({ role: "assistant", content: answer });
      }
      if (result.actions && result.actions.length) {
        renderPreview(result);
        setStatus("Draft തയ്യാറായി. സ്ഥിരീകരിക്കുന്നതിന് മുമ്പ് എല്ലാ വിവരങ്ങളും ചിത്രങ്ങളും പരിശോധിക്കുക.");
      } else {
        previewPanel.hidden = true;
        currentDraft = null;
        setStatus(result.needs_clarification ? "മാറ്റങ്ങൾ തയ്യാറാക്കുന്നതിന് മുമ്പ് assistant-ന് കൂടുതൽ വിവരങ്ങൾ വേണം." : "Website-ൽ മാറ്റങ്ങളൊന്നും തയ്യാറാക്കിയിട്ടില്ല.");
      }
      promptInput.value = "";
    } catch (error) {
      setStatus(error.message, "error");
      appendMessage("assistant", error.message);
    } finally {
      showWorking(false);
      updateConfirmState();
    }
  });

  confirmButton.addEventListener("click", async () => {
    if (!currentDraft || !confirmCheckbox.checked || busy) return;
    const actions = readDraftActions();
    const errors = checkRequired(actions);
    if (errors.length) {
      validationMessage.textContent = errors[0];
      validationMessage.classList.add("is-error");
      return;
    }
    const data = new FormData();
    data.set("proposal_id", currentDraft.proposal_id);
    data.set("actions", JSON.stringify(actions));
    data.set("review_confirmed", "yes");
    busy = true;
    updateConfirmState();
    setStatus("സ്ഥിരീകരിച്ച മാറ്റങ്ങൾ നടപ്പാക്കുന്നു…");
    try {
      const result = await postForm(app.dataset.confirmUrl, data);
      renderResults(result);
      history.push({ role: "assistant", content: "സ്ഥിരീകരിച്ച മാറ്റങ്ങൾ നടപ്പാക്കി." });
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      busy = false;
      updateConfirmState();
    }
  });

  cancelButton.addEventListener("click", async () => {
    if (!currentDraft) return;
    cancelButton.disabled = true;
    await cancelDraft();
    confirmCheckbox.checked = false;
    setStatus("Draft റദ്ദാക്കി. Website-ൽ മാറ്റമൊന്നും വരുത്തിയിട്ടില്ല.");
    cancelButton.disabled = false;
  });
})();
