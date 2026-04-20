const fs = require('fs');
const path = require('path');

const BASE = 'D:/chatgpt/c99c9a2d3817b3cfdb706409022ee0c04ad6e2c7a40c9428c8fe02b1aeb2689c-2026-03-01-10-56-41-21b2a2dc87b744dcaa8b4bcba7407fad';

// ─── Data collection ─────────────────────────────────────────────
const allConversations = [];
const userPrompts = [];
const conversationMeta = [];

// Load all conversation files
for (let i = 0; i <= 16; i++) {
  const fname = `conversations-${String(i).padStart(3, '0')}.json`;
  const fpath = path.join(BASE, fname);
  try {
    const data = JSON.parse(fs.readFileSync(fpath, 'utf8'));
    allConversations.push(...data);
  } catch (e) {
    console.error(`Error loading ${fname}:`, e.message);
  }
}

console.log(`Total conversations loaded: ${allConversations.length}`);

// Extract user messages and metadata
for (const conv of allConversations) {
  const title = conv.title || 'Untitled';
  const createTime = conv.create_time ? new Date(conv.create_time * 1000) : null;
  const updateTime = conv.update_time ? new Date(conv.update_time * 1000) : null;
  const model = conv.default_model_slug || 'unknown';
  const gizmoId = conv.gizmo_id || null;
  const isArchived = conv.is_archived || false;
  const isStarred = conv.is_starred || false;

  let userMsgCount = 0;
  let assistantMsgCount = 0;
  const convUserPrompts = [];

  if (conv.mapping) {
    for (const [nodeId, node] of Object.entries(conv.mapping)) {
      const msg = node.message;
      if (!msg || !msg.author) continue;

      if (msg.author.role === 'user') {
        userMsgCount++;
        let text = '';
        if (msg.content && msg.content.parts) {
          text = msg.content.parts
            .filter(p => typeof p === 'string')
            .join('\n')
            .trim();
        }
        if (text) {
          const timestamp = msg.create_time ? new Date(msg.create_time * 1000) : createTime;
          userPrompts.push({
            text,
            timestamp,
            conversationTitle: title,
            model,
            gizmoId,
            contentType: msg.content?.content_type || 'text',
            hasAttachments: msg.content?.parts?.some(p => typeof p !== 'string') || false,
          });
          convUserPrompts.push(text);
        }
      } else if (msg.author.role === 'assistant') {
        assistantMsgCount++;
      }
    }
  }

  conversationMeta.push({
    title,
    createTime,
    updateTime,
    model,
    gizmoId,
    isArchived,
    isStarred,
    userMsgCount,
    assistantMsgCount,
    totalTurns: userMsgCount + assistantMsgCount,
    firstPrompt: convUserPrompts[0] || '',
  });
}

console.log(`Total user prompts extracted: ${userPrompts.length}`);
console.log(`Date range: ${userPrompts.filter(p=>p.timestamp).map(p=>p.timestamp).sort((a,b)=>a-b)[0]?.toISOString()} to ${userPrompts.filter(p=>p.timestamp).map(p=>p.timestamp).sort((a,b)=>b-a)[0]?.toISOString()}`);

// ─── 1. TOPIC & USE CASE ANALYSIS ───────────────────────────────

const topicKeywords = {
  'Software Development / Coding': ['code', 'function', 'class', 'api', 'bug', 'error', 'debug', 'implement', 'refactor', 'typescript', 'javascript', 'python', 'php', 'react', 'node', 'sql', 'database', 'git', 'deploy', 'docker', 'test', 'unit test', 'symfony', 'laravel', 'nextjs', 'next.js', 'nestjs', 'express', 'mongodb', 'postgres', 'mysql', 'redis', 'aws', 'azure', 'gcp', 'terraform', 'ci/cd', 'pipeline', 'webpack', 'vite', 'eslint', 'prettier', 'npm', 'yarn', 'package', 'component', 'hook', 'state', 'props', 'interface', 'type', 'enum', 'migration', 'schema', 'endpoint', 'route', 'middleware', 'controller', 'service', 'repository', 'entity', 'dto', 'graphql', 'rest', 'crud', 'authentication', 'authorization', 'jwt', 'oauth', 'css', 'html', 'tailwind', 'styled', 'scss', 'sass'],
  'DevOps / Infrastructure': ['kubernetes', 'k8s', 'docker', 'container', 'helm', 'terraform', 'ansible', 'jenkins', 'github actions', 'ci/cd', 'pipeline', 'deploy', 'nginx', 'apache', 'load balancer', 'scaling', 'monitoring', 'grafana', 'prometheus', 'cloudwatch', 'vpc', 'subnet', 'ec2', 's3', 'lambda', 'serverless', 'microservice'],
  'Data & Analytics': ['data', 'analytics', 'dashboard', 'metric', 'report', 'chart', 'visualization', 'csv', 'excel', 'pandas', 'dataframe', 'etl', 'warehouse', 'bigquery', 'snowflake', 'tableau', 'power bi', 'statistics', 'aggregate'],
  'AI / Machine Learning': ['ai', 'machine learning', 'ml', 'model', 'neural', 'training', 'gpt', 'llm', 'prompt', 'embedding', 'vector', 'langchain', 'openai', 'anthropic', 'claude', 'chatgpt', 'fine-tune', 'rag', 'agent', 'transformer', 'deep learning', 'nlp', 'computer vision'],
  'Business / Strategy': ['business', 'strategy', 'market', 'revenue', 'growth', 'startup', 'saas', 'b2b', 'b2c', 'pricing', 'monetiz', 'competitor', 'pitch', 'investor', 'funding', 'roadmap', 'okr', 'kpi', 'stakeholder', 'roi', 'mvp', 'product market fit', 'go-to-market'],
  'Writing / Content': ['write', 'blog', 'article', 'content', 'copy', 'email', 'newsletter', 'post', 'story', 'essay', 'draft', 'edit', 'proofread', 'tone', 'headline', 'caption', 'script', 'presentation', 'slide', 'document'],
  'Career / Professional': ['resume', 'cv', 'job', 'interview', 'career', 'salary', 'negotiate', 'linkedin', 'portfolio', 'promotion', 'skills', 'certification', 'hiring', 'recruiter', 'cover letter'],
  'Product / UX Design': ['design', 'ux', 'ui', 'user experience', 'wireframe', 'mockup', 'prototype', 'figma', 'sketch', 'user flow', 'persona', 'usability', 'accessibility', 'responsive', 'mobile first', 'layout'],
  'Marketing / SEO': ['marketing', 'seo', 'sem', 'ads', 'campaign', 'conversion', 'funnel', 'brand', 'social media', 'instagram', 'twitter', 'linkedin post', 'google ads', 'facebook ads', 'engagement', 'audience', 'targeting', 'ctr', 'impression'],
  'E-commerce': ['ecommerce', 'e-commerce', 'shop', 'store', 'product', 'inventory', 'order', 'cart', 'checkout', 'payment', 'stripe', 'shopify', 'woocommerce', 'catalog', 'sku', 'fulfillment', 'shipping'],
  'Personal / Life': ['personal', 'health', 'fitness', 'diet', 'recipe', 'travel', 'book', 'movie', 'music', 'hobby', 'relationship', 'advice', 'recommend', 'suggest', 'opinion', 'think about', 'feel', 'help me understand'],
  'Education / Learning': ['learn', 'explain', 'tutorial', 'course', 'concept', 'understand', 'how does', 'what is', 'difference between', 'example', 'beginner', 'advanced', 'study', 'teach'],
  'Legal / Compliance': ['legal', 'gdpr', 'privacy', 'terms', 'contract', 'compliance', 'regulation', 'policy', 'license', 'copyright', 'trademark', 'patent', 'nda', 'liability'],
  'Finance / Crypto': ['crypto', 'bitcoin', 'ethereum', 'blockchain', 'defi', 'nft', 'token', 'wallet', 'trading', 'investment', 'stock', 'finance', 'fintech', 'banking'],
};

const topicCounts = {};
const topicExamples = {};
for (const topic of Object.keys(topicKeywords)) {
  topicCounts[topic] = 0;
  topicExamples[topic] = [];
}

for (const prompt of userPrompts) {
  const lower = prompt.text.toLowerCase();
  for (const [topic, keywords] of Object.entries(topicKeywords)) {
    const matched = keywords.some(kw => lower.includes(kw));
    if (matched) {
      topicCounts[topic]++;
      if (topicExamples[topic].length < 3) {
        topicExamples[topic].push(prompt.conversationTitle);
      }
    }
  }
}

// ─── 2. LINGUISTIC / NLP ANALYSIS ────────────────────────────────

// Prompt length stats
const lengths = userPrompts.map(p => p.text.length);
const wordCounts = userPrompts.map(p => p.text.split(/\s+/).length);
const avgLen = lengths.reduce((a,b) => a+b, 0) / lengths.length;
const avgWords = wordCounts.reduce((a,b) => a+b, 0) / wordCounts.length;
const medianWords = wordCounts.sort((a,b)=>a-b)[Math.floor(wordCounts.length/2)];
const maxWords = Math.max(...wordCounts);

// Sentence complexity
const sentenceCounts = userPrompts.map(p => p.text.split(/[.!?]+/).filter(s => s.trim()).length);
const avgSentences = sentenceCounts.reduce((a,b)=>a+b,0) / sentenceCounts.length;

// Question frequency
const questionPrompts = userPrompts.filter(p => p.text.includes('?'));
const questionRate = questionPrompts.length / userPrompts.length;

// Imperative vs interrogative vs declarative
let imperativeCount = 0;
let interrogativeCount = 0;
let declarativeCount = 0;
const imperativeVerbs = ['create', 'make', 'build', 'write', 'generate', 'fix', 'add', 'remove', 'update', 'change', 'implement', 'show', 'list', 'convert', 'explain', 'help', 'give', 'tell', 'find', 'search', 'refactor', 'optimize', 'design', 'set up', 'configure', 'deploy'];

for (const prompt of userPrompts) {
  const firstWord = prompt.text.trim().split(/\s+/)[0]?.toLowerCase();
  if (prompt.text.includes('?')) {
    interrogativeCount++;
  } else if (imperativeVerbs.some(v => firstWord === v || prompt.text.toLowerCase().startsWith(v))) {
    imperativeCount++;
  } else {
    declarativeCount++;
  }
}

// Code inclusion rate
const codePrompts = userPrompts.filter(p =>
  p.text.includes('```') ||
  p.text.includes('function ') ||
  p.text.includes('class ') ||
  p.text.includes('const ') ||
  p.text.includes('import ') ||
  p.text.includes('<?php') ||
  p.text.includes('def ') ||
  /\{[\s\S]*\}/.test(p.text) && p.text.length > 100
);
const codeRate = codePrompts.length / userPrompts.length;

// Language detection (rough)
const languageIndicators = {
  'English': /\b(the|is|are|was|were|have|has|this|that|with|for|and|but|not|can|will|how|what|why|when|please)\b/i,
  'Dutch': /\b(het|een|van|dat|dit|zijn|niet|maar|voor|met|ook|nog|wel|kan|moet|hebben|deze|wordt|naar)\b/i,
  'Turkish': /\b(bir|bu|için|ile|ve|olan|gibi|var|ben|sen|biz|nasıl|neden|ama|çok|olarak)\b/i,
  'German': /\b(der|die|das|ein|eine|ist|und|für|mit|auf|auch|nicht|sich|haben|werden|können)\b/i,
};

const langCounts = {};
for (const lang of Object.keys(languageIndicators)) langCounts[lang] = 0;

for (const prompt of userPrompts) {
  for (const [lang, regex] of Object.entries(languageIndicators)) {
    if (regex.test(prompt.text)) langCounts[lang]++;
  }
}

// ─── 3. COMMUNICATION STYLE PATTERNS ────────────────────────────

// Politeness markers
const politePrompts = userPrompts.filter(p => /\b(please|thank|thanks|could you|would you|kindly|appreciate)\b/i.test(p.text));
const politeRate = politePrompts.length / userPrompts.length;

// Formality (use of contractions, casual language)
const informalMarkers = userPrompts.filter(p => /\b(gonna|wanna|gotta|ain't|yeah|yep|nope|lol|haha|btw|fyi|tbh|imo|asap)\b/i.test(p.text));
const informalRate = informalMarkers.length / userPrompts.length;

// Direct vs contextual (does user provide context or just commands?)
const contextualPrompts = userPrompts.filter(p =>
  p.text.length > 200 ||
  /\b(context|background|currently|situation|working on|trying to|goal is|need to|purpose)\b/i.test(p.text)
);
const contextualRate = contextualPrompts.length / userPrompts.length;

// Follow-up patterns (short follow-ups vs standalone)
const shortPrompts = userPrompts.filter(p => p.text.split(/\s+/).length < 10);
const shortRate = shortPrompts.length / userPrompts.length;

// Technical jargon density
const techTerms = ['api', 'endpoint', 'middleware', 'microservice', 'containerize', 'orchestrat', 'deployment', 'ci/cd', 'pipeline', 'kubernetes', 'terraform', 'webhook', 'payload', 'schema', 'migration', 'serializ', 'deserializ', 'singleton', 'factory', 'observer', 'repository pattern', 'dependency injection', 'async', 'await', 'promise', 'callback', 'closure', 'recursion', 'polymorphism', 'inheritance', 'encapsulation', 'abstraction'];
let techTermTotal = 0;
for (const prompt of userPrompts) {
  const lower = prompt.text.toLowerCase();
  techTermTotal += techTerms.filter(t => lower.includes(t)).length;
}
const techDensity = techTermTotal / userPrompts.length;

// ─── 4. TEMPORAL ANALYSIS ────────────────────────────────────────

const hourCounts = new Array(24).fill(0);
const dayCounts = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const monthCounts = {};

for (const prompt of userPrompts) {
  if (prompt.timestamp) {
    hourCounts[prompt.timestamp.getHours()]++;
    dayCounts[prompt.timestamp.getDay()]++;
    const monthKey = `${prompt.timestamp.getFullYear()}-${String(prompt.timestamp.getMonth()+1).padStart(2,'0')}`;
    monthCounts[monthKey] = (monthCounts[monthKey] || 0) + 1;
  }
}

// Peak hours
const peakHour = hourCounts.indexOf(Math.max(...hourCounts));
const lateNight = hourCounts.slice(22).reduce((a,b)=>a+b,0) + hourCounts.slice(0,5).reduce((a,b)=>a+b,0);
const workHours = hourCounts.slice(9, 18).reduce((a,b)=>a+b,0);
const totalTimed = userPrompts.filter(p => p.timestamp).length;

// ─── 5. MODEL USAGE ─────────────────────────────────────────────

const modelCounts = {};
for (const conv of conversationMeta) {
  modelCounts[conv.model] = (modelCounts[conv.model] || 0) + 1;
}

// ─── 6. CONVERSATION DEPTH ──────────────────────────────────────

const turnDistribution = conversationMeta.map(c => c.totalTurns);
const avgTurns = turnDistribution.reduce((a,b)=>a+b,0) / turnDistribution.length;
const deepConvs = conversationMeta.filter(c => c.totalTurns > 20).length;
const singleTurnConvs = conversationMeta.filter(c => c.userMsgCount <= 1).length;

// ─── 7. GPT / Custom GPTs usage ─────────────────────────────────

const gizmoConvs = conversationMeta.filter(c => c.gizmoId);
const gizmoIds = {};
for (const c of gizmoConvs) {
  gizmoIds[c.gizmoId] = (gizmoIds[c.gizmoId] || 0) + 1;
}

// ─── 8. ADVANCED PATTERN: Prompt sophistication levels ───────────

let basicPrompts = 0;    // simple questions, single sentence
let intermediatePrompts = 0; // multi-sentence, some context
let advancedPrompts = 0;  // detailed specs, multi-part, code, constraints

for (const prompt of userPrompts) {
  const words = prompt.text.split(/\s+/).length;
  const sentences = prompt.text.split(/[.!?]+/).filter(s => s.trim()).length;
  const hasCode = /```|function |class |const |import |def /.test(prompt.text);
  const hasConstraints = /\b(must|should|don't|avoid|ensure|require|constraint|specific|exact)\b/i.test(prompt.text);
  const hasStructure = /\d+[\.\)]\s|[-*]\s/.test(prompt.text); // numbered/bulleted lists

  if (words > 100 || hasCode || (hasConstraints && sentences > 3) || hasStructure) {
    advancedPrompts++;
  } else if (words > 30 || sentences > 2) {
    intermediatePrompts++;
  } else {
    basicPrompts++;
  }
}

// ─── 9. RECURRING PHRASE PATTERNS (n-gram analysis) ──────────────

const bigramCounts = {};
const trigramCounts = {};

for (const prompt of userPrompts) {
  const words = prompt.text.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(w => w.length > 2);
  for (let i = 0; i < words.length - 1; i++) {
    const bigram = `${words[i]} ${words[i+1]}`;
    bigramCounts[bigram] = (bigramCounts[bigram] || 0) + 1;
  }
  for (let i = 0; i < words.length - 2; i++) {
    const trigram = `${words[i]} ${words[i+1]} ${words[i+2]}`;
    trigramCounts[trigram] = (trigramCounts[trigram] || 0) + 1;
  }
}

// Filter out common English stop-word n-grams
const stopBigrams = new Set(['in the', 'of the', 'to the', 'for the', 'and the', 'on the', 'with the', 'is the', 'it is', 'this is', 'that is', 'the following', 'i want', 'i need', 'can you', 'how to']);
const topBigrams = Object.entries(bigramCounts)
  .filter(([bg]) => !stopBigrams.has(bg))
  .sort((a,b) => b[1] - a[1])
  .slice(0, 25);

const topTrigrams = Object.entries(trigramCounts)
  .sort((a,b) => b[1] - a[1])
  .slice(0, 25);

// ─── 10. CONVERSATION TITLE WORD CLOUD ──────────────────────────

const titleWords = {};
for (const conv of conversationMeta) {
  if (!conv.title || conv.title === 'New chat' || conv.title === 'Untitled') continue;
  const words = conv.title.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(w => w.length > 2);
  for (const w of words) {
    titleWords[w] = (titleWords[w] || 0) + 1;
  }
}
const topTitleWords = Object.entries(titleWords).sort((a,b) => b[1] - a[1]).slice(0, 40);

// ─── 11. PROGRAMMING LANGUAGES USED ─────────────────────────────

const progLangKeywords = {
  'TypeScript/JavaScript': ['typescript', 'javascript', 'tsx', 'jsx', 'const ', 'let ', 'var ', '=>', 'async ', 'await ', 'import {', 'export ', 'interface ', 'type ', '.ts', '.js', 'react', 'next.js', 'nextjs', 'node', 'express', 'nestjs'],
  'PHP': ['<?php', 'php', 'symfony', 'laravel', 'eloquent', 'artisan', 'composer', 'namespace ', '->'],
  'Python': ['python', 'def ', 'import ', 'from ', 'pip', 'django', 'flask', 'pandas', 'numpy', '.py', 'self.'],
  'SQL': ['select ', 'insert ', 'update ', 'delete ', 'from ', 'where ', 'join ', 'table ', 'create table', 'alter table', 'index', 'query', 'sql'],
  'Shell/Bash': ['bash', 'shell', 'sh ', '#!/', 'chmod', 'grep', 'awk', 'sed', 'curl', 'wget'],
  'CSS/SCSS': ['css', 'scss', 'sass', 'tailwind', 'styled-components', 'flex', 'grid', 'media query', 'responsive'],
  'HTML': ['html', '<div', '<span', '<form', '<input', '<button', 'dom', 'element'],
  'Go': ['golang', 'func ', 'go ', 'goroutine', 'channel', 'defer', 'struct', 'package main'],
  'Rust': ['rust', 'cargo', 'fn ', 'impl ', 'trait ', 'struct ', 'enum ', 'match ', 'let mut'],
  'Java/Kotlin': ['java', 'kotlin', 'spring', 'maven', 'gradle', 'public class', 'void ', 'abstract'],
  'YAML/JSON Config': ['yaml', 'yml', 'json', 'dockerfile', 'docker-compose', 'helm', '.env'],
};

const progLangCounts = {};
for (const lang of Object.keys(progLangKeywords)) progLangCounts[lang] = 0;

for (const prompt of userPrompts) {
  const lower = prompt.text.toLowerCase();
  for (const [lang, kws] of Object.entries(progLangKeywords)) {
    if (kws.some(kw => lower.includes(kw))) {
      progLangCounts[lang]++;
    }
  }
}

// ─── OUTPUT RESULTS ──────────────────────────────────────────────

const results = {
  overview: {
    totalConversations: allConversations.length,
    totalUserPrompts: userPrompts.length,
    dateRange: {
      from: userPrompts.filter(p=>p.timestamp).map(p=>p.timestamp).sort((a,b)=>a-b)[0]?.toISOString(),
      to: userPrompts.filter(p=>p.timestamp).map(p=>p.timestamp).sort((a,b)=>b-a)[0]?.toISOString(),
    },
    avgPromptsPerConversation: (userPrompts.length / allConversations.length).toFixed(1),
    starredConversations: conversationMeta.filter(c => c.isStarred).length,
    archivedConversations: conversationMeta.filter(c => c.isArchived).length,
  },
  topicDistribution: Object.entries(topicCounts)
    .sort((a,b) => b[1] - a[1])
    .map(([topic, count]) => ({ topic, count, percentage: (count/userPrompts.length*100).toFixed(1) + '%' })),
  promptComplexity: {
    avgCharacterLength: Math.round(avgLen),
    avgWordCount: Math.round(avgWords),
    medianWordCount: medianWords,
    maxWordCount: maxWords,
    avgSentencesPerPrompt: avgSentences.toFixed(1),
    sophisticationLevels: {
      basic: `${basicPrompts} (${(basicPrompts/userPrompts.length*100).toFixed(1)}%)`,
      intermediate: `${intermediatePrompts} (${(intermediatePrompts/userPrompts.length*100).toFixed(1)}%)`,
      advanced: `${advancedPrompts} (${(advancedPrompts/userPrompts.length*100).toFixed(1)}%)`,
    },
  },
  communicationStyle: {
    sentenceTypes: {
      imperative: `${imperativeCount} (${(imperativeCount/userPrompts.length*100).toFixed(1)}%)`,
      interrogative: `${interrogativeCount} (${(interrogativeCount/userPrompts.length*100).toFixed(1)}%)`,
      declarative: `${declarativeCount} (${(declarativeCount/userPrompts.length*100).toFixed(1)}%)`,
    },
    politenessRate: (politeRate * 100).toFixed(1) + '%',
    informalLanguageRate: (informalRate * 100).toFixed(1) + '%',
    contextProvidingRate: (contextualRate * 100).toFixed(1) + '%',
    codeInclusionRate: (codeRate * 100).toFixed(1) + '%',
    shortPromptRate: (shortRate * 100).toFixed(1) + '%',
    techJargonDensity: techDensity.toFixed(2) + ' terms/prompt avg',
  },
  languageDistribution: Object.entries(langCounts)
    .sort((a,b) => b[1] - a[1])
    .map(([lang, count]) => ({ language: lang, prompts: count, percentage: (count/userPrompts.length*100).toFixed(1) + '%' })),
  programmingLanguages: Object.entries(progLangCounts)
    .sort((a,b) => b[1] - a[1])
    .filter(([,c]) => c > 0)
    .map(([lang, count]) => ({ language: lang, mentions: count, percentage: (count/userPrompts.length*100).toFixed(1) + '%' })),
  temporalPatterns: {
    peakHour: `${peakHour}:00`,
    hourlyDistribution: hourCounts.map((c, i) => `${String(i).padStart(2,'0')}:00 → ${c}`),
    dayOfWeekDistribution: Object.entries(dayCounts).map(([d, c]) => `${dayNames[d]}: ${c}`),
    lateNightUsage: `${(lateNight/totalTimed*100).toFixed(1)}% (22:00-05:00)`,
    workHoursUsage: `${(workHours/totalTimed*100).toFixed(1)}% (09:00-18:00)`,
    monthlyActivity: Object.entries(monthCounts).sort().map(([m, c]) => `${m}: ${c} prompts`),
  },
  modelUsage: Object.entries(modelCounts)
    .sort((a,b) => b[1] - a[1])
    .map(([model, count]) => ({ model, conversations: count })),
  conversationDepth: {
    avgTurnsPerConversation: avgTurns.toFixed(1),
    deepConversations: `${deepConvs} (>20 turns)`,
    singleTurnConversations: `${singleTurnConvs}`,
    maxTurns: Math.max(...turnDistribution),
  },
  customGPTsUsage: {
    conversationsWithGPTs: gizmoConvs.length,
    uniqueGPTsUsed: Object.keys(gizmoIds).length,
    topGPTs: Object.entries(gizmoIds).sort((a,b) => b[1] - a[1]).slice(0, 10),
  },
  topRecurringBigrams: topBigrams.map(([bg, c]) => `"${bg}": ${c}`),
  topRecurringTrigrams: topTrigrams.slice(0, 15).map(([tg, c]) => `"${tg}": ${c}`),
  topConversationTitleWords: topTitleWords.map(([w, c]) => `${w}: ${c}`),
};

fs.writeFileSync('D:/chatgpt/analysis_results.json', JSON.stringify(results, null, 2));
console.log('\nAnalysis complete. Results saved to analysis_results.json');

// Print summary
console.log('\n════════════════════════════════════════════════════════');
console.log('          CHATGPT CONVERSATION ANALYSIS SUMMARY');
console.log('════════════════════════════════════════════════════════\n');
console.log(JSON.stringify(results, null, 2));
