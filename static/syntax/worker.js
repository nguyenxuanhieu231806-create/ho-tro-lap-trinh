'use strict';

// This worker parses text only. It never runs code or sends it to an AI service.
importScripts('./tree-sitter.js');
const {Parser: SyntaxParser, Language} = self.Parser;
const ready = SyntaxParser.init({locateFile: name => new URL(name, self.location.href).href});
const grammars = {c: 'c', cpp: 'cpp', java: 'java', python: 'python'};
const parsers = new Map();
let newestId = 0;

function getParser(language) {
    if (!parsers.has(language)) {
        const loading = ready.then(async () => {
            const grammar = await Language.load(new URL(`tree-sitter-${grammars[language]}.wasm`, self.location.href).href);
            const parser = new SyntaxParser();
            parser.setLanguage(grammar);
            parser.setTimeoutMicros(150000);
            return parser;
        }).catch(error => { parsers.delete(language); throw error; });
        parsers.set(language, loading);
    }
    return parsers.get(language);
}

function diagnostics(tree, code) {
    const lines = code.split('\n');
    const issues = new Map();
    const pending = [tree.rootNode];
    let visited = 0;
    while (pending.length && issues.size < 40 && visited++ < 20000) {
        const node = pending.pop();
        if (!node.hasError && !node.isMissing && !node.isError) continue;
        const children = node.children;
        const faultyChildren = children.filter(child => child.hasError || child.isMissing || child.isError);
        if (node.isMissing || (node.isError && !faultyChildren.length)) {
            const point = node.startPosition;
            const line = Math.min(lines.length, point.row + 1);
            const column = Math.min(lines[line - 1].length + 1, point.column + 1);
            const missing = node.isMissing ? `Thiếu ký hiệu hoặc thành phần ${JSON.stringify(node.type)}.` : '';
            const message = missing || 'Cú pháp chưa hợp lệ gần vị trí này. Kiểm tra câu lệnh, dấu ngoặc và dấu kết thúc lệnh.';
            // A specific missing token is more useful than a broad parser error.
            if (!issues.has(line) || node.isMissing) {
                issues.set(line, {line, column, endColumn: Math.min(lines[line - 1].length + 1, column + 1),
                    severity: 'error', message});
            }
        }
        for (let i = faultyChildren.length - 1; i >= 0; i--) pending.push(faultyChildren[i]);
    }
    return [...issues.values()].sort((a, b) => a.line - b.line);
}

self.onmessage = async ({data}) => {
    const {id, language, code} = data || {};
    newestId = id;
    if (!Number.isSafeInteger(id) || !Object.hasOwn(grammars, language) || typeof code !== 'string') return;
    if (code.length > 60000) {
        self.postMessage({id, issues: [], error: 'Kiểm tra cú pháp nhanh hỗ trợ tối đa 60.000 ký tự.'});
        return;
    }
    let parser, tree;
    try {
        parser = await getParser(language);
        if (id !== newestId) return;
        tree = parser.parse(code);
        if (!tree) throw new Error('parse timeout');
        self.postMessage({id, issues: diagnostics(tree, code)});
    } catch (_) {
        parser?.reset();
        if (id === newestId) self.postMessage({id, issues: [], error: 'Chưa kiểm tra được cú pháp. Bạn vẫn có thể soạn thảo và hỏi AI.'});
    } finally {
        tree?.delete();
    }
};
