import json


def sql2json(rows):
    result = json.dumps(rows)
    return result

def group_by_category(rows):
    json_data = rows
    club_list = {}
    category_list = ["구기체육분과", "레저무예분과", "봉사분과", "어학분과", "연행예술분과", "인문사회분과", "자연과학분과", "종교분과", "창작비평분과", "가등록"]
    for category in category_list:
        club_list[category] = []

    # list type
    for club in json_data:
        club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id = club

        club_dict = {"club_name":club_name, "club_id":club_id, "club_img":club_img, "club_description":club_description, "opened":opened, "club_URL":club_URL, "leader_id":leader_id}
        club_list[category].append(club_dict)
    # dict type
    # for club in json_data:
    #     if club[4] not in club_list:
    #         club_list[club[4]] = {}
    #     club_list[club[4]][club[1]]= {'club_id':club[0], 'club_img':club[2], 'club_description':club[3], 'opened':club[5], 'club_URL':club[6]}
    return club_list


