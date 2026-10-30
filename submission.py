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
from public_feed import load_home_feed

submission = Blueprint('submission', __name__)


@submission.get('/')
@submission.get('/play')
@submission.get('/articles')
@submission.get('/preview/feed')
@submission.get('/preview/social')
def home():
    payload = load_home_feed(request.args.get('article', ''))
    if payload.get('requested_not_found'):
        abort(404, description='この記事は保存期間の終了などにより表示できません。')
    articles = [prepare_article(a) for a in payload['articles']]
    articles = attach_japan_connections(attach_timelines(articles))
    for article in articles:
        article['url_hash'] = hashlib.md5(article['url'].encode()).hexdigest()
        article['relation_quotes'] = []  # Raw quotations are not a relationship explainer.
        focus = article.get('focus') or {}
        article['focus'] = validate_focus(focus.get('point'), focus.get('evidence'), article['title'], article['description'])
        article['visual'], article['visual_label'] = fallback_visual(article)
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
        social_preview=True)


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
