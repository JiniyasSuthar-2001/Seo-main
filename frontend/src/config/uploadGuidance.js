/**
 * Single-source-of-truth for Upload Guidelines, Required/Optional Columns,
 * Synthetic Example Data, Data Privacy Warnings, and Help documentation.
 */

export const UPLOAD_GUIDELINES = {
    keywords: {
        id: 'keywords',
        title: 'Keyword Dataset Upload Guide',
        purpose: 'Import target keyword lists, search term frequencies, CPC, and difficulty metrics into your project workspace.',
        where_to_get: 'Export keyword lists from your rank-tracking software, keyword planner, or SEO analytics tool.',
        supported_formats: ['CSV', 'XLSX'],
        max_file_size: '25 MB',
        version: 'Version 1.2 — August 2026',
        required_columns: [
            { name: 'Keyword', description: 'Target search phrase', example: 'solar panels australia' }
        ],
        optional_columns: [
            { name: 'URL', description: 'Target landing page URL on your domain', example: 'https://example.com/solar-panels' },
            { name: 'Search Volume', description: 'Monthly search volume number', example: '2400' },
            { name: 'Position', description: 'External rank position (if available)', example: '5' },
            { name: 'Difficulty', description: 'Keyword difficulty percentage (0-100)', example: '45' },
            { name: 'CPC', description: 'Cost Per Click in USD/AUD', example: '3.50' },
            { name: 'Country', description: '2-letter country code', example: 'AU' },
            { name: 'Language', description: 'Target language', example: 'English' }
        ],
        synthetic_examples: [
            ['solar panels australia', 'https://example.com/solar-panels', '2400', '5', '45', '3.50', 'AU', 'English'],
            ['commercial electrician sydney', 'https://example.com/commercial', '1200', '12', '58', '5.20', 'AU', 'English'],
            ['emergency electrical repair', 'https://example.com/emergency', '880', '3', '32', '6.10', 'AU', 'English']
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
        supported_formats: ['CSV', 'XLSX'],
        max_file_size: '25 MB',
        version: 'Version 1.2 — August 2026',
        required_columns: [
            { name: 'Keyword', description: 'Ranked search phrase', example: 'electrician near me' },
            { name: 'URL', description: 'Ranking target URL on your domain', example: 'https://example.com/services' },
            { name: 'Position', description: 'Actual Google search rank position number', example: '8' }
        ],
        optional_columns: [
            { name: 'Search Volume', description: 'Monthly estimated volume', example: '3600' },
            { name: 'Country', description: 'Target geographic country code', example: 'AU' },
            { name: 'Device', description: 'Desktop or Mobile', example: 'Desktop' },
            { name: 'Search Engine', description: 'Search provider name', example: 'Google' },
            { name: 'Date', description: 'Snapshot ranking date (YYYY-MM-DD)', example: '2026-08-26' }
        ],
        synthetic_examples: [
            ['electrician near me', 'https://example.com/services', '8', '3600', 'AU', 'Desktop', 'Google', '2026-08-26'],
            ['solar battery installer', 'https://example.com/solar-batteries', '4', '1400', 'AU', 'Mobile', 'Google', '2026-08-26'],
            ['industrial wiring expert', 'https://example.com/industrial', '14', '590', 'AU', 'Desktop', 'Google', '2026-08-26']
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
        supported_formats: ['CSV', 'XLSX'],
        max_file_size: '25 MB',
        version: 'Version 1.2 — August 2026',
        required_columns: [
            { name: 'Source URL', description: 'External website URL containing the link', example: 'https://industry-news.com/top-electricians' },
            { name: 'Target URL', description: 'Your website URL being linked to', example: 'https://example.com/services' },
            { name: 'Anchor Text', description: 'Clickable text of the link', example: 'Licensed Sydney Electricians' }
        ],
        optional_columns: [
            { name: 'Referring Domain', description: 'External root domain name', example: 'industry-news.com' },
            { name: 'Link Type', description: 'Text, Image, or Redirect', example: 'Text' },
            { name: 'Follow/Nofollow', description: 'Follow, Nofollow, UGC, or Sponsored attribute', example: 'Follow' },
            { name: 'First Seen', description: 'Discovered date timestamp', example: '2026-01-15' },
            { name: 'Last Seen', description: 'Last verified date timestamp', example: '2026-08-20' }
        ],
        synthetic_examples: [
            ['https://industry-news.com/top-electricians', 'https://example.com/services', 'Licensed Sydney Electricians', 'industry-news.com', 'Text', 'Follow', '2026-01-15', '2026-08-20'],
            ['https://trade-directory.org/listings/solar', 'https://example.com/solar-panels', 'Visit Website', 'trade-directory.org', 'Text', 'Nofollow', '2026-03-10', '2026-08-22']
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
        where_to_get: 'Export competitor domain tracking datasets or SERP analysis files.',
        supported_formats: ['CSV', 'XLSX'],
        max_file_size: '25 MB',
        version: 'Version 1.2 — August 2026',
        required_columns: [
            { name: 'Competitor Domain', description: 'Competitor root domain name', example: 'competitor-electric.com' }
        ],
        optional_columns: [
            { name: 'Competitor Name', description: 'Company or business name', example: 'Competitor Electric Co' },
            { name: 'Competitor URL', description: 'Main website homepage URL', example: 'https://competitor-electric.com' },
            { name: 'Location', description: 'Geographic market location', example: 'Sydney, Australia' },
            { name: 'Overlapping Keywords', description: 'Count of shared search phrases', example: '450' }
        ],
        synthetic_examples: [
            ['competitor-electric.com', 'Competitor Electric Co', 'https://competitor-electric.com', 'Sydney, Australia', '450'],
            ['apex-solar-solutions.com.au', 'Apex Solar Solutions', 'https://apex-solar-solutions.com.au', 'Melbourne, Australia', '320']
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
        supported_formats: ['CSV', 'XLSX', 'ZIP'],
        max_file_size: '25 MB',
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
