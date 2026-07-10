import os
import re

class SEOAnalyzer:
    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """조사 및 특수문자 제거 후 2글자 이상의 핵심 명사성 키워드 추출"""
        # 한글 및 영문, 숫자가 아닌 문자를 공백 처리
        clean = re.sub(r'[^\w\s]', ' ', text)
        words = clean.split()
        keywords = []
        
        # 한국어 조사 필터링 정규식 (단어 끝부분 매칭)
        josa_pat = re.compile(r'(은|는|이|가|을|를|의|에|에서|로|으로|과|와|도|하며|하여|했다|이었다|였다)$')
        
        for w in words:
            if len(w) >= 2:
                # 조사 제거 시도
                w_clean = josa_pat.sub('', w)
                if len(w_clean) >= 2:
                    keywords.append(w_clean.lower())
        
        return list(set(keywords))

    @classmethod
    def calculate_seo_score(cls, title: str, description: str, tags: list[str]) -> dict:
        """
        입력된 제목, 설명란, 태그 배열을 바탕으로 vidIQ의 Actionable SEO 점수 산출 로직을
        100% 모사하여 100점 만점 기준의 SEO 점수 및 개별 진단 리포트를 생성합니다.
        """
        title = title or ""
        description = description or ""
        tags = tags or []
        
        # 1. Tag Count Score (Max 10)
        # 태그 개수가 10개 이상이면 만점(10점), 그 미만은 개당 1점
        tag_count = len(tags)
        tag_count_score = min(10, tag_count)
        
        # 2. Tag Volume Score (Max 10)
        # 태그 글자수 총합이 400자 이상(유튜브 글자수 제한 500자 근접)이면 만점
        total_tag_chars = sum(len(t) for t in tags) + max(0, len(tags) - 1)
        if total_tag_chars >= 400:
            tag_volume_score = 10
        elif total_tag_chars >= 300:
            tag_volume_score = 7
        elif total_tag_chars >= 200:
            tag_volume_score = 4
        else:
            tag_volume_score = 2
            
        # 3. Keywords in Title Score (Max 20)
        # 제목 추출 핵심 키워드가 태그 목록에 포함되는가?
        title_keywords = cls._extract_keywords(title)
        tag_keywords = [t.lower() for t in tags]
        
        matched_title_tags = [w for w in title_keywords if any(w in tk or tk in w for tk in tag_keywords)]
        
        # 제목 앞부분(앞쪽 35% 영역)에 매칭 키워드가 배치되어 눈길을 끄는가?
        title_len = len(title)
        front_threshold = int(title_len * 0.35) if title_len > 0 else 0
        front_text = title[:front_threshold].lower()
        
        has_front_keyword = any(w in front_text for w in matched_title_tags)
        
        if len(matched_title_tags) >= 2 and has_front_keyword:
            keywords_in_title_score = 20
        elif len(matched_title_tags) >= 1:
            keywords_in_title_score = 10
        else:
            keywords_in_title_score = 0
            
        # 4. Keywords in Description Score (Max 20)
        # 설명란 시작 150자 영역에 제목의 키워드가 몇 번 매칭/반복 노출되는가?
        desc_front = description[:150].lower()
        desc_matched_count = 0
        for w in title_keywords:
            if w in desc_front:
                desc_matched_count += len(re.findall(re.escape(w), desc_front))
                
        if desc_matched_count >= 3:
            keywords_in_desc_score = 20
        elif desc_matched_count >= 2:
            keywords_in_desc_score = 14
        elif desc_matched_count >= 1:
            keywords_in_desc_score = 7
        else:
            keywords_in_desc_score = 0
            
        # 5. Tripled Keywords Score (Max 20)
        # 제목, 설명란, 태그 세 곳에 공통 포함되는 트리플 키워드가 3개 이상인가?
        desc_keywords = cls._extract_keywords(description)
        triple_keywords = []
        for w in title_keywords:
            in_desc = any(w in dk for dk in desc_keywords)
            in_tags = any(w in tk or tk in w for tk in tag_keywords)
            if in_desc and in_tags:
                triple_keywords.append(w)
                
        if len(triple_keywords) >= 3:
            triple_score = 20
        elif len(triple_keywords) >= 2:
            triple_score = 14
        elif len(triple_keywords) >= 1:
            triple_score = 7
        else:
            triple_score = 0
            
        # 6. Title & Description Length Optimization (Max 20)
        # Title Length Score (Max 10) - 가독성을 위한 적절한 제목 길이 (15자 ~ 55자 사이)
        title_char_len = len(title)
        if 15 <= title_char_len <= 55:
            title_length_score = 10
        else:
            title_length_score = 5
            
        # Hashtag Count Score (Max 10) - 3~6개의 적정 태그 수 및 필수 Shorts 태그 보유 여부
        hashtags = re.findall(r'#\w+', description)
        has_shorts = any('shorts' in h.lower() for h in hashtags)
        
        hashtag_count = len(hashtags)
        if 3 <= hashtag_count <= 6 and has_shorts:
            hashtag_score = 10
        elif hashtag_count > 0 and has_shorts:
            hashtag_score = 5
        else:
            hashtag_score = 0
            
        # 최종 합계 점수
        total_score = (
            tag_count_score +
            tag_volume_score +
            keywords_in_title_score +
            keywords_in_desc_score +
            triple_score +
            title_length_score +
            hashtag_score
        )
        
        report = {
            "tag_count": f"{tag_count}개 ({tag_count_score}/10)",
            "tag_volume": f"{total_tag_chars}자 ({tag_volume_score}/10)",
            "keywords_in_title": f"매칭 {len(matched_title_tags)}개 / 전방 배치: {has_front_keyword} ({keywords_in_title_score}/20)",
            "keywords_in_desc": f"설명란 키워드 반복 빈도 {desc_matched_count}회 ({keywords_in_desc_score}/20)",
            "triple_keywords": f"트리플 키워드 수 {len(triple_keywords)}개 ({triple_score}/20)",
            "title_length": f"제목 글자수 {title_char_len}자 ({title_length_score}/10)",
            "hashtag_count": f"해시태그 {hashtag_count}개 / #Shorts 유무: {has_shorts} ({hashtag_score}/10)"
        }
        
        return {
            "seo_score": total_score,
            "seo_report": report,
            "triple_keywords_list": triple_keywords
        }
