document.querySelectorAll('[data-term-config]').forEach(quiz => {
  const article = quiz.closest('article');
  const config = JSON.parse(quiz.dataset.termConfig);
  let answered = false;
  const headline = article.querySelector('.headline-text');
  const originalTitle = headline.textContent;
  function show() {
    quiz.hidden = article.classList.contains('has-photo');
    article.classList.toggle('quiz-pending', !quiz.hidden && !answered);
    article.classList.toggle('quiz-done', !quiz.hidden && answered);
    if (config.kind === 'headline') headline.textContent = !quiz.hidden && !answered ? config.question : originalTitle;
  }
  function finish(choice) {
    if (answered) return;
    answered = true;
    if (config.kind === 'headline') quiz.querySelector('.term-word').textContent = config.options[config.answer];
    quiz.querySelectorAll('.quiz-choices button').forEach((button, index) => {
      button.disabled = true;
      button.classList.toggle('right', index === config.answer);
      button.classList.toggle('wrong', choice === index && index !== config.answer);
    });
    quiz.querySelector('.quiz-feedback').textContent = (choice === config.answer ? '正解！ ' : '正解は ') + config.options[config.answer];
    const explanation = quiz.querySelector('.term-explanation');
    explanation.textContent = config.explanation;
    explanation.hidden = false;
    quiz.querySelector('.term-source').hidden = false;
    const notes = quiz.querySelector('.quiz-notes');
    if (notes) notes.hidden = false;
    show();
  }
  config.options.forEach((text, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = text;
    button.addEventListener('click', () => finish(index));
    quiz.querySelector('.quiz-choices').append(button);
  });
  quiz.querySelector('.quiz-skip').addEventListener('click', () => finish(null));
  article.querySelectorAll('button[data-kind]').forEach(button => button.addEventListener('click', () => { if (!answered && !quiz.hidden) finish(null); }));
  article.addEventListener('photo-ready', show);
  article.addEventListener('photo-unavailable', show);
  show();
});
