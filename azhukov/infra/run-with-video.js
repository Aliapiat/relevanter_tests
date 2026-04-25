#!/usr/bin/env node

/**
 * Запуск Playwright тестов с записью видео и опциональной склейкой.
 *
 * Использование:
 *   node scripts/run-with-video.js TC-009              # только запуск с видео
 *   node scripts/run-with-video.js TC-009 --glue       # запуск + склейка в один файл
 *   node scripts/run-with-video.js TC-009 --glue-only  # только склейка (тесты уже прошли)
 *
 * Переменные окружения (автоматически выставляются):
 *   VIDEO=on        — запись видео
 *   SLOW_MO=1000    — задержка 1 секунда между действиями
 */

const { execSync, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);
const testPattern = args.find(a => !a.startsWith('--')) || 'TC-009';
const doGlue = args.includes('--glue') || args.includes('--glue-only');
const glueOnly = args.includes('--glue-only');

const rootDir = path.resolve(__dirname, '..');
const resultsDir = path.join(rootDir, 'test-results');
const outputVideo = path.join(rootDir, 'results', `${testPattern}-merged.webm`);
const ffmpegBin = require('ffmpeg-static');

// ── 1. Запуск тестов ────────────────────────────────────────────────

if (!glueOnly) {
  console.log(`\n▶ Запуск тестов: ${testPattern} (VIDEO=on, SLOW_MO=1000)\n`);

  const result = spawnSync(
    'npx',
    ['playwright', 'test', testPattern, '--workers', '1'],
    {
      cwd: rootDir,
      stdio: 'inherit',
      shell: true,
      env: {
        ...process.env,
        VIDEO: 'on',
        SLOW_MO: '1000',
      },
      timeout: 600_000, // 10 минут макс
    },
  );

  console.log(`\n✓ Тесты завершены (код: ${result.status})\n`);
}

// ── 2. Склейка видео (--glue / --glue-only) ────────────────────────

if (!doGlue) {
  console.log('Видео сохранены в test-results/. Для склейки добавьте --glue');
  process.exit(0);
}

console.log('\n▶ Склейка видео...\n');

if (!fs.existsSync(resultsDir)) {
  console.error('Папка test-results/ не найдена — сначала запустите тесты');
  process.exit(1);
}

// Собираем все .webm файлы из test-results
function findVideos(dir) {
  const videos = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      videos.push(...findVideos(fullPath));
    } else if (entry.name.endsWith('.webm')) {
      videos.push(fullPath);
    }
  }
  return videos;
}

const allVideos = findVideos(resultsDir);

if (allVideos.length === 0) {
  console.error('Видео не найдены в test-results/');
  process.exit(1);
}

// Сортировка: по имени папки (Playwright именует по тесту)
// Порядок: overview/UI тесты первые, потом поисковые кейсы
// Ключевые слова из ОБРЕЗАННЫХ имён папок Playwright (последний фрагмент названия теста)
const ORDER_KEYWORDS = [
  'модалка-фильтры-поиск',  // 1. Полный обход UI (обзорный тест — всегда первый)
  'фильтры-без-hh',         // 2. Фильтры без HH-секций
  'релевантных-кандидатов',  // 3. Поиск по должности
  'должность-зарплата',      // 4. Фильтры сужают выдачу
  'source-estaff',           // 5. Базовый поиск
  'мужского-пола',           // 6. Пол М
  'женского-пола',           // 7. Пол Ж
  'в-диапазоне',             // 8. Возраст 25-35
  '100k-200k',               // 9. Зарплата
  'результаты-релевантны',   // 10. Должность «менеджер»
  'мужчины-в-диапазоне',     // 11. Комбинация М + возраст
  'фильтра-применены',       // 12. Комбинация должность + зарплата
  'более-6-лет',             // 13. Опыт >6 лет (fallback: "параметр-передаётся" но неуникален)
  'вариантов-опыта',         // 14. Несколько опыта
  'передаётся-корректно',    // 15. Навыки skillGroups
  'стоп-лист',               // 16. Стоп-лист
  'доноры',                  // 17. Компании-доноры
  'текущая-компания',        // 18. Текущая компания (E-Staff)
  'предыдущая-компания',     // 19. Предыдущая компания (E-Staff)
  'женщины-с',               // 20. Комбинация Ж + должность
];

function sortOrder(filePath) {
  const normalized = filePath.replace(/\\/g, '/').toLowerCase();
  for (let i = 0; i < ORDER_KEYWORDS.length; i++) {
    if (normalized.includes(ORDER_KEYWORDS[i].toLowerCase())) return i;
  }
  return ORDER_KEYWORDS.length;
}

allVideos.sort((a, b) => sortOrder(a) - sortOrder(b));

console.log(`Найдено ${allVideos.length} видео:`);
allVideos.forEach((v, i) => {
  const rel = path.relative(resultsDir, v);
  console.log(`  ${i + 1}. ${rel}`);
});

// Создаём concat-файл для ffmpeg
const concatFile = path.join(resultsDir, 'concat-list.txt');
const concatContent = allVideos
  .map(v => `file '${v.replace(/\\/g, '/')}'`)
  .join('\n');
fs.writeFileSync(concatFile, concatContent, 'utf-8');

// Создаём папку results/ если нет
fs.mkdirSync(path.dirname(outputVideo), { recursive: true });

const outPath = outputVideo.replace(/\\/g, '/');
const concatPath = concatFile.replace(/\\/g, '/');

// Читаем тайминги загрузки (тест записывает когда ожидание HR-Proxy начинается/заканчивается)
const timingFile = path.join(resultsDir, 'video-timing.jsonl');
let timings = [];
if (fs.existsSync(timingFile)) {
  timings = fs.readFileSync(timingFile, 'utf-8')
    .trim().split('\n')
    .filter(Boolean)
    .map(line => JSON.parse(line));
  console.log(`Тайминги загрузки: ${timings.length} записей`);
}

// Обрабатываем каждое видео отдельно: ускоряем загрузку в 100 раз
const processedDir = path.join(resultsDir, '_processed');
fs.mkdirSync(processedDir, { recursive: true });
const processedVideos = [];

// Тайминги в порядке выполнения тестов = порядку видео после сортировки (ORDER_KEYWORDS).
// Тесты 1-2 (UI) — короткие (<30с), без таймингов.
// Тесты 3-20 — длинные (>30с), все пишут тайминги.
let timingIdx = 0;

for (let vi = 0; vi < allVideos.length; vi++) {
  const videoPath = allVideos[vi].replace(/\\/g, '/');
  const outName = `${vi + 1}.webm`;
  const processedPath = path.join(processedDir, outName).replace(/\\/g, '/');

  // Получаем длительность видео
  let videoDuration = 0;
  try {
    const probeOut = execSync(`"${ffmpegBin}" -i "${videoPath}" -f null - 2>&1`, { encoding: 'utf-8', timeout: 30_000 });
    const m = probeOut.match(/Duration:\s*(\d+):(\d+):([\d.]+)/);
    if (m) videoDuration = parseInt(m[1]) * 3600 + parseInt(m[2]) * 60 + parseFloat(m[3]);
  } catch {}

  // Находим тайминг для этого видео (если есть ожидание > 3с)
  const timing = (timingIdx < timings.length && videoDuration > 30) ? timings[timingIdx++] : null;

  if (!timing || timing.waitSec < 5) {
    // Короткое видео или нет ожидания — копируем как есть
    fs.copyFileSync(videoPath.replace(/\//g, path.sep), processedPath.replace(/\//g, path.sep));
    processedVideos.push(processedPath);
    const rel = path.relative(resultsDir, allVideos[vi]);
    console.log(`  ${vi + 1}. ${rel} → без изменений (${videoDuration.toFixed(0)}с)`);
    continue;
  }

  // Ускоряем загрузку: trim до клика | trim ожидание (100x) | trim после ответа
  const { loadStartSec, loadEndSec, waitSec } = timing;
  const rel = path.relative(resultsDir, allVideos[vi]);
  console.log(`  ${vi + 1}. ${rel} → ускорение ${loadStartSec.toFixed(0)}s-${loadEndSec.toFixed(0)}s (${waitSec.toFixed(0)}с → ${(waitSec / 100).toFixed(1)}с)`);

  const segments = [];
  const labels = [];
  let si = 0;

  // Часть до загрузки
  if (loadStartSec > 0.1) {
    segments.push(`[0:v]trim=0:${loadStartSec.toFixed(3)},setpts=PTS-STARTPTS[v${si}]`);
    labels.push(`[v${si}]`);
    si++;
  }
  // Загрузка (ускорение 100x)
  segments.push(`[0:v]trim=${loadStartSec.toFixed(3)}:${loadEndSec.toFixed(3)},setpts=(PTS-STARTPTS)/100[v${si}]`);
  labels.push(`[v${si}]`);
  si++;
  // Часть после загрузки
  if (videoDuration > loadEndSec + 0.1) {
    segments.push(`[0:v]trim=${loadEndSec.toFixed(3)}:${videoDuration.toFixed(3)},setpts=PTS-STARTPTS[v${si}]`);
    labels.push(`[v${si}]`);
    si++;
  }

  segments.push(`${labels.join('')}concat=n=${labels.length}:v=1[out]`);
  const filter = segments.join('; ');

  try {
    execSync(
      `"${ffmpegBin}" -y -i "${videoPath}" -filter_complex "${filter}" -map "[out]" -c:v libvpx -b:v 1M "${processedPath}"`,
      { stdio: 'pipe', timeout: 120_000 },
    );
    processedVideos.push(processedPath);
  } catch {
    // Fallback: копируем оригинал
    fs.copyFileSync(videoPath.replace(/\//g, path.sep), processedPath.replace(/\//g, path.sep));
    processedVideos.push(processedPath);
    console.log(`    ⚠ ffmpeg ошибка, используем оригинал`);
  }
}

// Concat все обработанные видео
console.log(`\nСклейка ${processedVideos.length} видео...`);
const finalConcatFile = path.join(processedDir, 'concat.txt');
fs.writeFileSync(finalConcatFile, processedVideos.map(v => `file '${v}'`).join('\n'));
const finalConcatPath = finalConcatFile.replace(/\\/g, '/');

try {
  execSync(
    `"${ffmpegBin}" -y -f concat -safe 0 -i "${finalConcatPath}" -c copy "${outPath}"`,
    { stdio: 'inherit' },
  );
  console.log(`\n✓ Склеено (загрузка ускорена 100x): ${path.relative(rootDir, outputVideo)}`);
} catch {
  // Fallback: перекодируем
  try {
    execSync(
      `"${ffmpegBin}" -y -f concat -safe 0 -i "${finalConcatPath}" -c:v libvpx -b:v 1M "${outPath}"`,
      { stdio: 'inherit', timeout: 600_000 },
    );
    console.log(`\n✓ Склеено (перекодировано): ${path.relative(rootDir, outputVideo)}`);
  } catch {
    console.error('Ошибка финальной склейки');
  }
}

// Очистка
fs.rmSync(processedDir, { recursive: true, force: true });

// Очистка
fs.unlinkSync(concatFile);
