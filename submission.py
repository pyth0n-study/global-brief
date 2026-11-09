"""Public submission experience. Rendering never calls news or AI APIs."""
import json
import hashlib
from pathlib import Path
from flask import Blueprint, render_template, request, abort
from article_presentation import prepare_article
from preview_visuals import fallback_visual, world_paths
from timeline_library import attach_timelines, load_timelines
from japan_connections import attach_japan_connections
from grounded_focus import validate_focus
from history_quizzes import history_cover_for_article
from public_feed import load_home_feed

submission = Blueprint('submission', __name__)


@submission.get('/')
@submission.get('/play')
@submission.get('/articles')
@submission.get('/preview/feed')
@submission.get('/preview/social')
@submission.get('/preview/acronyms')
@submission.get('/preview/flags')
def home():
    payload = load_home_feed(request.args.get('article', ''))
    if payload.get('requested_not_found'):
        abort(404, description='この記事は保存期間の終了などにより表示できません。')
    acronym_preview = request.path == '/preview/acronyms'
    articles = [prepare_article(a, prefer_acronym=acronym_preview) for a in payload['articles']]
    if acronym_preview:
        articles = [a for a in articles if (a.get('term_quiz') or {}).get('kind') == 'acronym']
        if not articles:
            abort(404, description='現在、自動照合できた略語問題はありません。')
    flag_preview = request.path == '/preview/flags'
    if request.path != '/articles':
        import secrets
        from flag_quizzes import flag_quiz
        mode = request.args.get('quiz', '') if flag_preview else ''
        for item in articles:
            flag = flag_quiz(item.get('quiz_country'))
            if flag and (mode == 'flag' or (mode != 'map' and secrets.randbelow(2) == 0)):
                item['quiz'] = None
                item['quiz_country'] = None
                item['term_quiz'] = flag
    articles = attach_japan_connections(attach_timelines(articles))
    for article in articles:
        article['url_hash'] = hashlib.md5(article['url'].encode()).hexdigest()
        article['relation_quotes'] = []  # Raw quotations are not a relationship explainer.
        focus = article.get('focus') or {}
        article['focus'] = validate_focus(focus.get('point'), focus.get('evidence'), article['title'], article['description'])
        article['visual'], article['visual_label'] = fallback_visual(article)
        if request.path != '/articles':
            cover = history_cover_for_article(article)
            if cover:
                article['history_cover'] = cover
                article['image'] = ''
                article['visual_label'] = ''
    if request.path == '/articles':
        from app import get_category, CATEGORY_COLORS
        for article in articles:
            article['category'] = get_category(article['title'])
            article['banner_color'] = CATEGORY_COLORS[article['category']]
            article['url_hash'] = hashlib.md5(article['url'].encode()).hexdigest()
            article['content'] = article.get('summary') or article['description_excerpt']
            article['friendly_title'] = article['display_title']
        return render_template('index.html', news=articles, trends=[], error=False,
            submission_mode=True, captured_at=payload['captured_at'], news_provider='newsdata')
    template = 'image_preview.html'
    return render_template(template, articles=articles, inline_quiz=True,
        motion=False, countries=world_paths(), timelines=load_timelines(),
        submission_mode=True, captured_at=payload['captured_at'], separated_feed=True, immersive_feed=True,
        live_archive=payload.get('live_archive', False), archive_status=payload.get('archive_status', {}),
        social_preview=True, acronym_preview=acronym_preview, flag_preview=flag_preview)


@submission.get('/about')
def about():
    from_list = request.args.get('from') == 'list'
    return render_template('submission_about.html', back_url='/articles' if from_list else '/',
        back_label='記事一覧に戻る' if from_list else 'ニュースに戻る')


@submission.get('/background')
def background():
    from news_archive import seed_archive, read_archive, COUNTRIES, THEMES
    from background_guides import guides_for
    country, theme = request.args.get('country', ''), request.args.get('theme', '')
    active_tab = 'archive' if request.args.get('tab') == 'archive' else 'basics'
    if (country and country not in COUNTRIES) or (theme and theme not in THEMES):
        abort(400)
    seed_archive()
    from archive_store import sync_public_archive
    archive_status = sync_public_archive()
    articles = read_archive(country, theme)
    for item in articles:
        item.update(prepare_article(item))
    return render_template('background.html', countries=COUNTRIES, themes=THEMES,
        country=country, theme=theme, guides=guides_for(country, theme), articles=articles, archive_status=archive_status, active_tab=active_tab)
