(function() {
    const SUPPORTED_LANGUAGES = ['es', 'en', 'pt', 'fr'];
    const DEFAULT_LANGUAGE = 'es';
    let currentLanguage = DEFAULT_LANGUAGE;

    // Obtener idioma inicial con manejo robusto de excepciones (soporte para navegación privada)
    try {
        const savedLang = localStorage.getItem('web_language');
        if (savedLang && SUPPORTED_LANGUAGES.includes(savedLang)) {
            currentLanguage = savedLang;
        } else {
            // Detectar idioma del navegador
            const browserLang = (navigator.language || navigator.userLanguage || '').split('-')[0].toLowerCase();
            if (SUPPORTED_LANGUAGES.includes(browserLang)) {
                currentLanguage = browserLang;
            }
        }
    } catch (e) {
        console.warn('localStorage no está disponible o está bloqueado. Usando detección del navegador:', e);
        const browserLang = (navigator.language || navigator.userLanguage || '').split('-')[0].toLowerCase();
        if (SUPPORTED_LANGUAGES.includes(browserLang)) {
            currentLanguage = browserLang;
        }
    }

    // Función principal para traducir los elementos del DOM
    function translateDOM(lang) {
        if (!window.WEB_TRANSLATIONS || !window.WEB_TRANSLATIONS[lang]) {
            console.error(`Diccionario de traducción no cargado para el idioma: ${lang}`);
            return;
        }

        const dict = window.WEB_TRANSLATIONS[lang];
        const fallbackDict = window.WEB_TRANSLATIONS[DEFAULT_LANGUAGE];

        // Buscar todos los elementos etiquetados para traducción
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            let translatedText = dict[key] || fallbackDict[key];

            if (translatedText !== undefined) {
                // Prevención de XSS y manejo de contenido:
                // Si el elemento es un input/textarea, traducimos su placeholder
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    el.setAttribute('placeholder', translatedText);
                } else {
                    // Usamos textContent para evitar inyección XSS de forma segura
                    el.textContent = translatedText;
                }
            }
        });

        // Actualizar estado activo en los botones de selección de idioma en el Navbar
        const langButtons = document.querySelectorAll('.lang-btn');
        langButtons.forEach(btn => {
            const btnLang = btn.getAttribute('data-lang');
            if (btnLang === lang) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Actualizar el atributo lang del HTML para accesibilidad
        document.documentElement.setAttribute('lang', lang);

        // Traducir dinámicamente el título del documento (browser tab) de forma segura
        try {
            const titleParts = document.title.split(' - ');
            if (titleParts.length > 1) {
                let pageKey = 'web_home';
                const path = window.location.pathname;
                if (path.includes('/commands')) pageKey = 'web_commands';
                else if (path.includes('/docs')) pageKey = 'web_docs_title';
                else if (path.includes('/profile')) pageKey = 'web_profile_title';
                else if (path.includes('/terms')) pageKey = 'web_terms_of_service';
                else if (path.includes('/privacy')) pageKey = 'web_privacy_policy';

                const pageName = dict[pageKey] || fallbackDict[pageKey];
                if (pageName) {
                    document.title = `${titleParts[0]} - ${pageName}`;
                }
            }
        } catch (e) {
            console.error('Error al actualizar el título del documento:', e);
        }
    }

    // Exponer la función globalmente de forma segura
    window.setLanguage = function(lang) {
        if (!SUPPORTED_LANGUAGES.includes(lang)) {
            lang = DEFAULT_LANGUAGE;
        }
        currentLanguage = lang;
        
        try {
            localStorage.setItem('web_language', lang);
        } catch (e) {
            console.error('No se pudo guardar la preferencia de idioma en localStorage:', e);
        }
        
        translateDOM(lang);
    };

    // Ejecutar la traducción inicial en cuanto el DOM esté listo
    document.addEventListener('DOMContentLoaded', () => {
        // Enlazar eventos de clic en los botones de idioma de la Navbar de forma dinámica y robusta
        const langButtons = document.querySelectorAll('.lang-btn');
        langButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const selectedLang = btn.getAttribute('data-lang');
                window.setLanguage(selectedLang);
            });
        });

        // Traducir al idioma detectado al cargar la página
        translateDOM(currentLanguage);
    });
})();
