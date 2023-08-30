from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Post, Like as Like_Model, Comment, PostImage 
from user.models import Profile
from .serializers import PostSerializer
from user.serializers import ProfileSerializer, UserSerializer
from rest_framework.views import APIView
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404


User = get_user_model()
# Create your views here.


class CommentWrite(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        post = Post.objects.get(id=request.data['post_id'])
        
        comment = Comment.objects.create(writer=user,content=request.data['content'],post=post,parent_comment=None)
        
        datas = {
            "message": "댓글 생성 완료",
        }
        return Response(datas,status=status.HTTP_201_CREATED)


class CommentEdit(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        comment = Comment.objects.get(id=request.data['comment_id'])
        comment.content = request.data['comment']
        comment.save()
        
        datas = {
            "message": "댓글 수정 완료",
        }
        
        return Response(datas,status=status.HTTP_200_OK)


class CommentDelete(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        comment = Comment.objects.get(id=request.data['comment_id'])
        comment.is_active = False
        comment.save()
        
        datas = {
            "message": "댓글 삭제 완료",
        }
        return Response(datas,status=status.HTTP_200_OK)
    

class ReCommentWrite(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        post = Post.objects.get(id=request.data['post_id'])
        parent_comment = Comment.objects.get(id=request.data['comment_id'])
        
        comment = Comment.objects.create(writer=user,content=request.data['content'],post=post,parent_comment=parent_comment)
        
        datas = {
            "message": "대댓글 생성 완료",
        }
        return Response(datas,status=status.HTTP_201_CREATED)


class Unlike(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        post_id = request.data.get('post_id')
        user = request.user

        post = get_object_or_404(Post, pk=post_id)
        like = Like_Model.objects.filter(post=post, user=user).first()

        if like:
            like.delete()
            return Response({"detail": "Post unliked successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "You haven't liked this post before."}, status=status.HTTP_400_BAD_REQUEST)


class Like(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        post_id = request.data.get('post_id')
        user = request.user

        post = get_object_or_404(Post, pk=post_id)
        like, created = Like_Model.objects.get_or_create(post=post, user=user)

        if created:
            return Response({"detail": "Post liked successfully."}, status=status.HTTP_201_CREATED)
        else:
            return Response({"detail": "You've already liked this post."}, status=status.HTTP_400_BAD_REQUEST)


## Post
class List(APIView):
    def get(self, request):
        posts = Post.objects.filter(is_active=True).order_by('-created_at')
        recent_posts = posts[:5]
        
        data = []
        for post in posts:
            writer = post.writer
            profile = UserSerializer(writer)
            likes = Like_Model.objects.filter(post_id=post.id).count()
            images = post.image.all()  # 이미지들 가져오기
            
            post_info = {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "views": post.views,
                "images": [{"image": image.image.url} for image in images],
                "created_at": post.created_at,
                "updated_at": post.updated_at,
            }
            
            add_new = {
                "post": post_info,
                "likes": likes,
                "writer": profile.data
            }
            
            data.append(add_new)
        
        response_data = {
            "posts": data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)



class RecentPost(APIView):
    def get(self, request):
        recent_posts = Post.objects.filter(is_active=True).order_by('-created_at')[:5]

        response_data = {
            "recent_posts": PostSerializer(recent_posts, many=True).data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class Write(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        post_data = {
            'title': request.data['title'],
            'content': request.data['content'],
            'writer': user
        }
        images = request.FILES.getlist('images')  

        post = Post.objects.create(**post_data)

        for image in images:
            PostImage.objects.create(post=post, image=image)

        data = {
            "message": "글 생성 완료"
        }
        return Response(data, status=status.HTTP_201_CREATED)



class Edit(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        post = Post.objects.get(id=pk)

        post.title = request.data.get('title', post.title)
        post.content = request.data.get('content', post.content)
        post.save()

        prev_imgs = PostImage.objects.filter(post=post) 
        prev_imgs.delete() 
        
        # 변경: 'postImage'에서 'images'로 수정
        images_data = request.FILES.getlist('images') 

        for image_data in images_data:
            PostImage.objects.create(post=post, image=image_data)

        data = {
            "message": "글 수정 완료"
        }

        return Response(data, status=status.HTTP_200_OK)
    

class Delete(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            post = Post.objects.get(id=pk)
        except ObjectDoesNotExist:
            raise Http404
        
        images = post.image.all()
        for image in images:
            image.image.delete()  
            image.delete()  
        
        post.is_active = False
        post.save()
        
        data = {
            "message": "글 삭제 완료"
        }
        return Response(data, status=status.HTTP_200_OK)


class View(APIView):
    # 좋아요, 글 정보, 댓글과 대댓글 구분
    def post(self, request, pk):

        raw_post = Post.objects.get(id=pk)
        raw_post.views = raw_post.views + 1
        raw_post.save()
        
        comments = Comment.objects.filter(post=raw_post).values()
        likes = Like_Model.objects.filter(post=raw_post).values()
        writer = Profile.objects.filter(user=raw_post.writer_id).values() # 이전 
        writer = User.objects.get(id=raw_post.writer_id) # 이
        images = raw_post.image.all()  
        
        comments_infos = []
        
        for comment in comments:
            comments_info = {} 
            comment_writer = Profile.objects.filter(user=comment['writer_id']).values()
            comments_info['comment'] = comment
            comments_info['writer'] = comment_writer[0]
            comments_infos.append(comments_info)
        
        post_data = PostSerializer(raw_post).data
        post_data["images"] = [{"image": image.image.url} for image in images]
        post_data["likes"] = len(likes)
        
        writer_data = ProfileSerializer(writer[0]).data if writer else None # 이전
        writer_data = UserSerializer(writer).data if writer else None # 이후
        
        data = {
            "post": post_data,
            "comments": comments_infos,
            "likes": likes,
            "writer": writer_data
        }
        
        return Response(data, status=status.HTTP_200_OK)

    
class PostSearch(APIView):
    def post(self, request):
        query = request.data.get('query') 
        
        if query is None:
            return Response({"error": "Missing 'query' parameter"}, status=400)

        profiles = Profile.objects.filter(Q(nickname__icontains=query) | Q(about__icontains=query),is_active=True)
        profile_serializer = ProfileSerializer(profiles, many=True)
        
        posts = Post.objects.filter(Q(title__icontains=query) | Q(content__icontains=query),is_active=True).order_by('-created_at')
        post_serializers = PostSerializer(posts, many=True).data

        new_postlist = []
        for p_s in post_serializers:
            writer = Profile.objects.get(user=p_s['writer'])
            writer_info = ProfileSerializer(writer).data
            info = {
                'post': p_s,
                'writer': writer_info
            }
            new_postlist.append(info)
        
        
        response_data = {
            "profiles": profile_serializer.data,
            "posts": new_postlist
        }
        
        return Response(response_data)







