// Theme toggle functionality
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
        toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

// Initialize theme from localStorage
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

// Highlight current page in navigation
function highlightCurrentNav() {
    const currentPath = window.location.pathname;
    const currentPage = currentPath.split('/').pop() || 'index.html';
    
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        const linkPage = href.split('/').pop();
        
        if (linkPage === currentPage || 
            (currentPage === '' && linkPage === 'index.html') ||
            (currentPage === 'index.html' && linkPage === 'index.html')) {
            link.classList.add('active');
        }
    });
}

// Mobile menu toggle
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('mobile-open');
}

// Close mobile menu when clicking outside
function closeMobileMenuOnOutsideClick(event) {
    const sidebar = document.querySelector('.sidebar');
    const toggle = document.querySelector('.mobile-menu-toggle');
    
    if (sidebar.classList.contains('mobile-open') && 
        !sidebar.contains(event.target) && 
        !toggle.contains(event.target)) {
        sidebar.classList.remove('mobile-open');
    }
}

// Close mobile menu when clicking a nav link
function setupMobileNavLinks() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.remove('mobile-open');
        });
    });
}

// Simple client-side search
function initSearch() {
    const searchInput = document.querySelector('.search-input');
    if (!searchInput) return;
    
    const searchIndex = [
        { title: 'Home', url: 'index.html', keywords: 'home overview introduction ups riello shutdown' },
        { title: 'Architecture Overview', url: 'architecture/overview.html', keywords: 'architecture overview system design components' },
        { title: 'Project Structure', url: 'architecture/project-structure.html', keywords: 'project structure files folders organization' },
        { title: 'Dependencies', url: 'architecture/dependencies.html', keywords: 'dependencies python requirements packages' },
        { title: 'Entities', url: 'domain/entities.html', keywords: 'entities classes domain model' },
        { title: 'Relationships', url: 'domain/relationships.html', keywords: 'relationships data flow connections' },
        { title: 'Business Rules', url: 'domain/business-rules.html', keywords: 'business rules logic constraints' },
        { title: 'API Endpoints', url: 'api/endpoints.html', keywords: 'api endpoints http rest' },
        { title: 'Authentication', url: 'api/authentication.html', keywords: 'authentication security access' },
        { title: 'Error Handling', url: 'api/error-handling.html', keywords: 'error handling exceptions status codes' },
        { title: 'Service Reference', url: 'services/service-reference.html', keywords: 'services systemd daemon' },
        { title: 'Database Schema', url: 'data/database-schema.html', keywords: 'database schema sqlite tables' },
        { title: 'Data Access', url: 'data/data-access.html', keywords: 'data access queries database' },
        { title: 'Getting Started', url: 'guides/getting-started.html', keywords: 'getting started setup installation' },
        { title: 'Use Cases', url: 'guides/use-cases.html', keywords: 'use cases examples code' }
    ];
    
    let searchResults = null;
    
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        
        if (!searchResults) {
            searchResults = document.createElement('div');
            searchResults.className = 'search-results';
            searchResults.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: var(--bg-color);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                margin-top: 4px;
                max-height: 300px;
                overflow-y: auto;
                box-shadow: var(--shadow-lg);
                z-index: 1000;
            `;
            searchInput.parentElement.style.position = 'relative';
            searchInput.parentElement.appendChild(searchResults);
        }
        
        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }
        
        const results = searchIndex.filter(item => 
            item.title.toLowerCase().includes(query) || 
            item.keywords.includes(query)
        );
        
        if (results.length === 0) {
            searchResults.innerHTML = '<div style="padding: 1rem; color: var(--text-muted);">No results found</div>';
        } else {
            searchResults.innerHTML = results.map(item => `
                <a href="${item.url}" style="
                    display: block;
                    padding: 0.75rem 1rem;
                    color: var(--text-color);
                    text-decoration: none;
                    border-bottom: 1px solid var(--border-color);
                " onmouseover="this.style.backgroundColor='var(--bg-secondary)'" 
                   onmouseout="this.style.backgroundColor='transparent'">
                    ${item.title}
                </a>
            `).join('');
        }
        
        searchResults.style.display = 'block';
    });
    
    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        if (searchResults && !searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
}

// Smooth scroll for anchor links
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Copy code button functionality
function initCodeCopy() {
    document.querySelectorAll('pre').forEach(pre => {
        const button = document.createElement('button');
        button.textContent = '📋';
        button.title = 'Copy code';
        button.style.cssText = `
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            padding: 0.25rem 0.5rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: var(--bg-color);
            cursor: pointer;
            font-size: 0.875rem;
            opacity: 0;
            transition: opacity 0.2s;
        `;
        
        pre.style.position = 'relative';
        pre.appendChild(button);
        
        pre.addEventListener('mouseenter', () => {
            button.style.opacity = '1';
        });
        
        pre.addEventListener('mouseleave', () => {
            button.style.opacity = '0';
        });
        
        button.addEventListener('click', async () => {
            const code = pre.querySelector('code');
            if (code) {
                try {
                    await navigator.clipboard.writeText(code.textContent);
                    button.textContent = '✓';
                    setTimeout(() => {
                        button.textContent = '📋';
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy:', err);
                }
            }
        });
    });
}

// Initialize Mermaid if present
function initMermaid() {
    if (typeof mermaid !== 'undefined') {
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default';
        mermaid.initialize({
            startOnLoad: true,
            theme: theme,
            securityLevel: 'loose'
        });
    }
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    highlightCurrentNav();
    setupMobileNavLinks();
    initSearch();
    initSmoothScroll();
    initCodeCopy();
    initMermaid();
    
    // Add click listener for mobile menu
    document.addEventListener('click', closeMobileMenuOnOutsideClick);
    
    // Initialize Prism.js if present
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
});

// Re-initialize Mermaid when theme changes
document.querySelector('.theme-toggle')?.addEventListener('click', () => {
    setTimeout(initMermaid, 100);
});
