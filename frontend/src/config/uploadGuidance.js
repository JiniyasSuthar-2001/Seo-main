/**
 * Single-source-of-truth for Upload Guidelines, Required/Optional Columns,
 * Synthetic Example Data, Data Privacy Warnings, and Help documentation.
 */

export const SHARED_UPLOAD_CONFIG = {
    supported_formats: ['CSV', 'XLSX', 'XLS', 'JSON'],
    supported_extensions: ['.csv', '.xlsx', '.xls', '.json'],
    max_file_size_mb: 10,
    max_file_size_label: '10 MB',
    accepted_mime_types: '.csv,.xlsx,.xls,.json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/json',
    validation_rules: [
        'File size must not exceed 10 MB limit.',
        'File format must be valid .csv, .xlsx, .xls, or .json.',
        'File must contain required columns for the dataset type.',
        'Do not upload sensitive data, passwords, or API keys.'
    ],
    error_messages: {
        file_too_large: 'File size exceeds maximum allowed limit of 10 MB.',
        unsupported_format: 'Unsupported file format. Please upload a .csv, .xlsx, .xls, or .json file.',
        empty_file: 'The selected file contains no readable data rows.',
        sensitive_data: 'Potential sensitive information or credentials detected in file.'
    }
};

export const EMPTY_IMPORT_HISTORY_MESSAGE = "No previous file imports recorded for this website project.";

export const UPLOAD_GUIDELINES = {
    keywords: {
        id: 'keywords',
        title: 'Keyword Dataset Upload Guide',
        purpose: 'Import target keyword lists, search term frequencies, CPC, difficulty, and intent metrics into your project workspace.',
        where_to_get: 'Export keyword lists from Google Search Console, rank-tracking tools, or SEO keyword planners.',
        supported_formats: SHARED_UPLOAD_CONFIG.supported_formats,
        max_file_size: SHARED_UPLOAD_CONFIG.max_file_size_label,
        version: 'Version 1.3 — September 2026',
        required_columns: [
            { name: 'Keyword', description: 'Target search phrase (Required)', example: 'seo audit checklist' }
        ],
        optional_columns: [
            { name: 'Target URL', description: 'Target landing page URL on your domain (e.g. https://example.com/page)', example: 'https://example.com/blog/seo-audit' },
            { name: 'Search Volume', description: 'Estimated monthly search queries (integer >= 0)', example: '3600' },
            { name: 'Difficulty', description: 'Keyword difficulty score between 0 and 100', example: '42' },
            { name: 'CPC', description: 'Cost Per Click in currency units (decimal number)', example: '4.20' },
            { name: 'Intent', description: 'Search intent: Informational, Commercial, Transactional, Navigational', example: 'Informational' },
            { name: 'Position', description: 'Google SERP position rank if available (integer 1-100)', example: '8' },
            { name: 'Country', description: '2-letter ISO country code (e.g. US, AU, GB)', example: 'US' }
        ],
        synthetic_examples: [
            ['seo audit checklist', 'https://example.com/blog/seo-audit', '3600', '42', '4.20', 'Informational', '8', 'US'],
            ['enterprise technical seo', 'https://example.com/services/technical-seo', '1200', '65', '8.50', 'Commercial', '3', 'US'],
            ['local seo agency sydney', 'https://example.com/locations/sydney', '880', '51', '6.75', 'Transactional', '5', 'AU'],
            ['page speed optimization service', 'https://example.com/services/page-speed', '1450', '38', '5.10', 'Commercial', '12', 'US'],
            ['xml sitemap generator tool', 'https://example.com/tools/sitemap', '5400', '29', '2.80', 'Navigational', '2', 'GB']
        ],
        common_errors: [
            'Keyword frequency in HTML does NOT equal Google SERP ranking.',
            'If Position column is missing, Google Position will report as "Not available".',
            'Search Volume must be a numeric integer.'
        ],
        privacy_warning: 'Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data.'
    },

    rankings: {
        id: 'rankings',
        title: 'Search Ranking Dataset Upload Guide',
        purpose: 'Import genuine historical search engine ranking positions exported from a rank tracking provider or Google Search Console.',
        where_to_get: 'Export position history from your rank tracking platform, Search Console performance export, or SERP provider.',
        supported_formats: SHARED_UPLOAD_CONFIG.supported_formats,
        max_file_size: SHARED_UPLOAD_CONFIG.max_file_size_label,
        version: 'Version 1.3 — September 2026',
        required_columns: [
            { name: 'Keyword', description: 'Ranked search phrase (Required)', example: 'seo audit services' },
            { name: 'URL', description: 'Ranking target URL on your domain (Required)', example: 'https://example.com/services/audit' },
            { name: 'Position', description: 'Actual Google search rank position number (1-100, Required)', example: '4' }
        ],
        optional_columns: [
            { name: 'Search Volume', description: 'Monthly estimated search volume (integer >= 0)', example: '4500' },
            { name: 'Country', description: 'Target geographic country code (e.g. US, AU, GB)', example: 'US' },
            { name: 'Device', description: 'Target device type: Desktop or Mobile', example: 'Desktop' },
            { name: 'Search Engine', description: 'Search provider name (e.g. Google, Bing)', example: 'Google' },
            { name: 'Date', description: 'Snapshot ranking date in ISO format (YYYY-MM-DD)', example: '2026-09-01' }
        ],
        synthetic_examples: [
            ['seo audit services', 'https://example.com/services/audit', '4', '4500', 'US', 'Desktop', 'Google', '2026-09-01'],
            ['best backlink checker', 'https://example.com/tools/backlinks', '7', '8200', 'US', 'Desktop', 'Google', '2026-09-01'],
            ['local seo consultant', 'https://example.com/consulting', '3', '1900', 'AU', 'Mobile', 'Google', '2026-09-01'],
            ['ecommerce schema markup', 'https://example.com/guides/schema', '11', '950', 'GB', 'Desktop', 'Google', '2026-09-01'],
            ['broken link checker free', 'https://example.com/tools/broken-links', '6', '6100', 'US', 'Mobile', 'Google', '2026-09-01']
        ],
        common_errors: [
            'Position must be a positive integer between 1 and 100.',
            'Never calculate Google position from internal page keyword count.',
            'Date format should be YYYY-MM-DD or MM/DD/YYYY.'
        ],
        privacy_warning: 'Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data.'
    },

    backlinks: {
        id: 'backlinks',
        title: 'Inbound Backlink Dataset Upload Guide',
        purpose: 'Import external inbound backlinks linking from external websites TO your target domain.',
        where_to_get: 'Export backlink reports from your SEO analytics tool or Google Search Console links report.',
        supported_formats: SHARED_UPLOAD_CONFIG.supported_formats,
        max_file_size: SHARED_UPLOAD_CONFIG.max_file_size_label,
        version: 'Version 1.3 — September 2026',
        required_columns: [
            { name: 'Source URL', description: 'External website URL containing the inbound link (Required)', example: 'https://tech-journal.com/top-seo-tools-2026' },
            { name: 'Target URL', description: 'Your website destination URL being linked to (Required)', example: 'https://example.com/services/audit' },
            { name: 'Anchor Text', description: 'Clickable anchor text of the link (Required)', example: 'Comprehensive SEO Audit Suite' }
        ],
        optional_columns: [
            { name: 'Referring Domain', description: 'External root domain name (e.g. tech-journal.com)', example: 'tech-journal.com' },
            { name: 'Follow/Nofollow', description: 'Link rel attribute: Follow, Nofollow, UGC, or Sponsored', example: 'Follow' },
            { name: 'Status', description: 'Backlink status: Active or Lost', example: 'Active' },
            { name: 'First Seen', description: 'Initial discovery date timestamp (YYYY-MM-DD)', example: '2026-02-10' },
            { name: 'Last Seen', description: 'Last verified crawl date timestamp (YYYY-MM-DD)', example: '2026-08-15' }
        ],
        synthetic_examples: [
            ['https://tech-journal.com/top-seo-tools-2026', 'https://example.com/services/audit', 'Comprehensive SEO Audit Suite', 'tech-journal.com', 'Follow', 'Active', '2026-02-10', '2026-08-15'],
            ['https://marketing-insider.org/resources', 'https://example.com/blog/seo-audit', 'SEO Guide', 'marketing-insider.org', 'Nofollow', 'Active', '2026-03-22', '2026-08-20'],
            ['https://industry-directory.net/agencies', 'https://example.com/', 'Visit Website', 'industry-directory.net', 'Follow', 'Active', '2026-01-05', '2026-08-18'],
            ['https://dev-community.io/discussions/crawlers', 'https://example.com/tools/sitemap', 'fast sitemap tool', 'dev-community.io', 'UGC', 'Active', '2026-05-14', '2026-08-25'],
            ['https://business-weekly.com/news/digital-trends', 'https://example.com/services/technical-seo', 'Technical SEO Specialist', 'business-weekly.com', 'Sponsored', 'Active', '2026-06-01', '2026-08-22']
        ],
        common_errors: [
            'Outbound links on your site are separate from inbound backlinks pointing to your site.',
            'Source URL must be a valid HTTP/HTTPS web address.',
            'Do not include login credentials or API keys in CSV fields.'
        ],
        privacy_warning: 'Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data.'
    },

    competitors: {
        id: 'competitors',
        title: 'Competitor Dataset Upload Guide',
        purpose: 'Import verified competitor domain lists and keyword overlap records for market intelligence.',
        where_to_get: 'Export competitor domain tracking datasets or SERP competitive analysis files.',
        supported_formats: SHARED_UPLOAD_CONFIG.supported_formats,
        max_file_size: SHARED_UPLOAD_CONFIG.max_file_size_label,
        version: 'Version 1.3 — September 2026',
        required_columns: [
            { name: 'Competitor Domain', description: 'Competitor root domain name (e.g. bright-seo-solutions.com, Required)', example: 'bright-seo-solutions.com' }
        ],
        optional_columns: [
            { name: 'Competitor Name', description: 'Company or business brand name', example: 'Bright SEO Solutions' },
            { name: 'Location', description: 'Primary geographic market location', example: 'New York, USA' },
            { name: 'Overlapping Keywords', description: 'Count of shared search ranking phrases (integer >= 0)', example: '840' },
            { name: 'Relevance Score', description: 'Market relevance percentage score between 0.0 and 100.0', example: '88.5' }
        ],
        synthetic_examples: [
            ['bright-seo-solutions.com', 'Bright SEO Solutions', 'New York, USA', '840', '88.5'],
            ['apex-digital-search.co.uk', 'Apex Digital Search', 'London, UK', '620', '79.2'],
            ['pacific-rankings.com.au', 'Pacific Rankings', 'Sydney, Australia', '490', '74.0'],
            ['vanguard-organic.com', 'Vanguard Organic Growth', 'Chicago, USA', '310', '65.8'],
            ['summit-search-partners.com', 'Summit Search Partners', 'San Francisco, USA', '950', '92.4']
        ],
        common_errors: [
            'Do NOT upload competitor internal credentials, private accounts, or customer lists.',
            'Competitor domain should be clean (e.g. competitor.com without http://).'
        ],
        privacy_warning: 'Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data.'
    },

    gsc: {
        id: 'gsc',
        title: 'Google Search Console Export Upload Guide',
        purpose: 'Import performance metrics exported from Google Search Console.',
        where_to_get: 'Export Performance tables directly from Google Search Console (Queries, Pages, Countries, Devices).',
        supported_formats: SHARED_UPLOAD_CONFIG.supported_formats,
        max_file_size: SHARED_UPLOAD_CONFIG.max_file_size_label,
        version: 'Version 1.2 — August 2026',
        required_columns: [
            { name: 'Top queries / Query / Page', description: 'Search term or page URL', example: 'solar installation cost' },
            { name: 'Clicks', description: 'Total clicks received', example: '145' },
            { name: 'Impressions', description: 'Total search impressions', example: '2800' }
        ],
        optional_columns: [
            { name: 'CTR', description: 'Click Through Rate percentage', example: '5.18%' },
            { name: 'Position', description: 'Average SERP position', example: '6.4' }
        ],
        synthetic_examples: [
            ['solar installation cost', '145', '2800', '5.18%', '6.4'],
            ['commercial electrician quote', '92', '1450', '6.34%', '4.2']
        ],
        common_errors: [
            'Do NOT manually insert Google OAuth tokens or client secrets into Search Console CSV files.',
            'For live direct sync, use the "Connect Account" OAuth integration instead.'
        ],
        privacy_warning: 'Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data.'
    }
};

export function getUploadGuidance(guidelineId) {
    return UPLOAD_GUIDELINES[guidelineId] || UPLOAD_GUIDELINES.keywords;
}
