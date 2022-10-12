import json


def sql2json(rows):
    result = json.dumps(rows)
    return result

def group_by_category(rows):
    json_data = rows
    print(json_data[0])
    club_list = {}

    # list type
    for club in json_data:
        club_id, club_name, club_img, club_description, category, opened, club_URL = club
        club_dict = {"club_name":club_name, "club_id":club_id, "club_img":club_img, "club_description":club_description, "opened":opened, "club_URL":club_URL}
        if category not in club_list:
            club_list[category] = []
        club_list[club[4]].append(club_dict)
    # dict type
    # for club in json_data:
    #     if club[4] not in club_list:
    #         club_list[club[4]] = {}
    #     club_list[club[4]][club[1]]= {'club_id':club[0], 'club_img':club[2], 'club_description':club[3], 'opened':club[5], 'club_URL':club[6]}
    return club_list


# {
# 	스포츠:{
# 		탁구동아리:{
# 			ID:1
# 			소개: 탁구동아리입니다.
# 			이미지:http://fdsafdas/fdasfdas/fff
# 		},
# 		배드민턴동아리:{
# 			ID:3
# 			소개: 동아리입니다.
# 			이미지:http://fdsafdas/fdasfdas/fff
# 		}
# 	},
# 	컴퓨터:{
# 		비빔밥:{
# 			ID:3
# 			소개: 동아리입니다.
# 			이미지:http://fdsafdas/fdasfdas/fff
# 		},
# 		반바지:{
# 			ID:4
# 			소개: 동아리입니다.
# 			이미지:http://fdsafdas/fdasfdas/fff
# 		}
# 	}
# }
